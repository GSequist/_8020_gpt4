"""please for any changes to code let me know thanks @george"""

import os
from urllib.parse import unquote
from typing import Dict
import gc
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect, HTTPException
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import shutil
import urllib
import uvicorn
import json
import asyncio
from function_caller import chat_completion_with_function_execution
from ingest import process_documents
from utils import (
    Conversation,
    url_sessions,
    sources_url_sessions,
    sources_sessions,
    user_sessions,
    conversations,
    WORK_FOLDER,
)


app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


############################################################################################################
## startup logic


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("web.html", {"request": request})


@app.on_event("startup")
async def startup_event():
    os.makedirs(WORK_FOLDER, exist_ok=True)


############################################################################################################
## first listener logic


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    print(f"webSocket accepted for user: {user_id}")
    user_sessions[user_id] = websocket

    if user_id not in conversations:
        conversations[user_id] = Conversation()
        await initialize_conversation(user_id)
    else:
        await send_previous_conversations(user_id, websocket)
        print(f"\n[websocket_endpoint]: sending previous conversations")

    # incoming messages
    try:
        while True:
            data = await websocket.receive_text()
            data_json = json.loads(data)

            # handle other types of messages
            if data_json.get("type") == "request_previous_conversations":
                print("[websocket_endpoint]: requesting previous conversations")
                await send_previous_conversations(user_id, websocket)
            if data_json.get("type") == "request_last_assistant_message":
                await send_last_assistant_message(user_id, websocket)
            else:
                await handle_message(user_id, data_json, websocket)

    except WebSocketDisconnect:
        print(f"\nwebSocket disconnected for user: {user_id}")
        user_sessions.pop(user_id, None)

        # cleanup user files
        user_folder = os.path.join(WORK_FOLDER, user_id)
        if os.path.exists(user_folder):
            shutil.rmtree(user_folder)
        print(f"\ncleaned up files for user on disconnect: {user_folder}")
        # cleanup user faiss
        user_faiss_folder = f"faiss_db_{user_id}"
        if os.path.exists(user_faiss_folder):
            shutil.rmtree(user_faiss_folder)
            print(f"\ncleaned FAISS folder for user on disconnect: {user_faiss_folder}")

        # run garbage collector
        collected_objects = gc.collect()
        print(f"\ncollected {collected_objects} unreachable objects.")


############################################################################################################
## file management


@app.get("/files/{user_id}")
async def list_files_for_user(user_id: str):
    user_folder = os.path.join(WORK_FOLDER, user_id)
    if not os.path.exists(user_folder):
        return []
    files = os.listdir(user_folder)
    return files


MAX_TOTAL_SIZE_MB = 30


def get_total_size(user_id: str) -> int:
    """get the total size of files in the user's directory."""
    user_folder = os.path.join(WORK_FOLDER, user_id)
    total_size = 0
    if os.path.exists(user_folder):
        for file in os.listdir(user_folder):
            total_size += os.path.getsize(os.path.join(user_folder, file))
    return total_size


@app.post("/upload/{user_id}")
async def upload_file(user_id: str, file: UploadFile = File(...)) -> Dict[str, str]:
    total_size = get_total_size(user_id)
    file_size = os.fstat(file.file.fileno()).st_size
    if total_size + file_size > MAX_TOTAL_SIZE_MB * 1024 * 1024:
        return {"status": "error", "message": ">file size exceeded"}
    file_path = f"{WORK_FOLDER}/{user_id}/{file.filename}"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    process_documents(user_id, os.path.dirname(file_path))
    return {"status": "success", "fileName": file.filename}


@app.delete("/delete/{user_id}/{file_name}")
async def delete_file(user_id: str, file_name: str):
    decoded_file_name = unquote(file_name)
    user_folder = os.path.join(WORK_FOLDER, user_id)
    file_path = os.path.join(user_folder, decoded_file_name)
    print(f"\n[delete_file]: deleting file: {file_path}")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        os.remove(file_path)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


############################################################################################################
## download handler


@app.get("/download/{user_id}")
async def download_file(user_id: str, file: str):
    decoded_file = urllib.parse.unquote(file)
    file_path = os.path.join(WORK_FOLDER, user_id, decoded_file)
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            filename=file,
        )
    return {"error": "File not found."}


############################################################################################################
## conversation management


async def initialize_conversation(user_id: str):
    conversations[user_id] = Conversation()


async def send_previous_conversations(user_id: str, websocket: WebSocket):
    retrieved_conversation_history = conversations[user_id].get_conversation_history()
    if retrieved_conversation_history:
        message = json.dumps(
            {"type": "previous_conversations", "data": retrieved_conversation_history}
        )
        print(
            f"\n[send_previous_conversations]: sending previous conversations: {retrieved_conversation_history}"
        )
        await websocket.send_text(message)


async def send_last_assistant_message(user_id: str, websocket: WebSocket):
    last_assistant_message = get_last_message_of_role(
        conversations[user_id].get_conversation_history(), "assistant"
    )
    if last_assistant_message:
        message = json.dumps(
            {"type": "last_assistant_message", "data": last_assistant_message}
        )
        await websocket.send_text(message)


def get_last_message_of_role(conversation_history, role):
    for message in reversed(conversation_history):
        if message["role"] == role:
            print(f"\n[get_last_message_of_role]: last message: {message}")
            return message
    return None


############################################################################################################
## message handling


async def handle_message(user_id, data, websocket):
    """main wrapper function handling the full interaction from a message received from the client."""
    print(f"\n[handle_message]: received data: {data}")

    print(f"\n[handle_message] userid received: {user_id}")
    query = data.get("message")

    if query:
        print(f"\n[handle_message]: inserting chat text...{query}")

        conversations[user_id].add_message("user", query)

        # emit the user's new message
        message = json.dumps({"type": "new_user_message", "data": query})
        await websocket.send_text(message)

        response_generator = chat_completion_with_function_execution(
            conversations[user_id].conversation_history, user_id, websocket
        )

        # collect chunks
        full_response = ""
        compl_response = ""

        async for response in response_generator:
            if isinstance(response, str):
                full_response = response
                compl_response += full_response

                message = json.dumps({"type": "response", "data": full_response})

                await websocket.send_text(message)
                await asyncio.sleep(0.01)

        if user_id in url_sessions:
            payload = {
                "img_url": url_sessions[user_id].get("img_url", ""),
            }
            message = json.dumps({"type": "response", "data": "", "payload": payload})
            await websocket.send_text(message)
            print(
                f"[handle_message]: URL emitted (first 100 chars): {payload['img_url'][:100]}"
            )
            url_sessions[user_id]["img_url"] = ""

        if user_id in sources_sessions:
            sources = sources_sessions[user_id]
            message = json.dumps({"type": "sources", "data": "", "sources": sources})
            await websocket.send_text(message)
            print(f"\n[handle_message]: sources emitted: {sources}")

            # clear sources
            sources_sessions[user_id] = {"combined": []}

        if user_id in sources_url_sessions:
            sources_url = sources_url_sessions[user_id].get("sources_url", "")
            message = json.dumps(
                {"type": "sources_url", "data": "", "sources_url": sources_url}
            )
            await websocket.send_text(message)
            print(f"\n[handle_message]: sources url emitted: {sources_url}")

            # clear sources
            sources_url_sessions[user_id] = {"sources_url": []}

        conversations[user_id].add_message("assistant", compl_response)

        conversations[user_id].abbreviate_function_messages()

        conversations[user_id].display_conversation()

        message = json.dumps({"type": "endOfMessage", "data": ""})
        await websocket.send_text(message)


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

############################################################################################################
