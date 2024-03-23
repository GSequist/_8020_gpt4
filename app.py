"""please for any changes to code let me know thanks @george"""

import os
import io
from urllib.parse import unquote
from typing import Dict
import gc
from dotenv import load_dotenv
from openai import AsyncOpenAI
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
    proofreading_sessions,
    audio_preferences,
    conversations,
    WORK_FOLDER,
)

load_dotenv()


client = AsyncOpenAI()

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
        await initialize_conversation(user_id)
    else:
        await send_previous_conversations(user_id, websocket)
        print(f"\n[websocket_endpoint]: sending previous conversations")

    # incoming messages
    try:
        while True:
            data = await websocket.receive_text()
            data_json = json.loads(data)

            if data_json.get("type") == "delete_conversation":
                conversations[user_id].delete_conversation()
                print(f"\nConversation for user {user_id} deleted.")
                await websocket.close(reason="Conversation deleted")
                return
            elif data_json.get("type") == "request_previous_conversations":
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
    user_folder = os.path.join(WORK_FOLDER, user_id)
    os.makedirs(user_folder, exist_ok=True)
    file_path = os.path.join(user_folder, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    img_extensions = {".png", ".jpg", ".webp"}
    file_extension = os.path.splitext(file.filename)[1].lower()

    if file_extension not in img_extensions:
        process_documents(user_id, file_path, user_folder)
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

    data_type = data.get("type")

    if data_type == "toggle_audio":
        audio_preferences[user_id] = data.get("isAudioEnabled", False)
        return

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
        if audio_preferences.get(user_id, False):
            if len(compl_response) > 4096:
                compl_response = compl_response[-4096:]
            spoken_response = await client.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=compl_response,
                response_format="mp3",
            )

            buffer = io.BytesIO()
            buffer.write(spoken_response.content)
            buffer.seek(0)
            audio_data = buffer.read()

            await websocket.send_bytes(audio_data)
            print(f"\n[handle_message]: audio emitted {audio_data[:100]}")
        else:
            print(f"\n[handle_message]: audio not requested")

        if user_id in proofreading_sessions:
            proofread_doc = proofreading_sessions[user_id]
            print(f"Type of proofread_doc: {type(proofread_doc)}")
            message = json.dumps({"type": "proofreading", "data": proofread_doc})
            await websocket.send_text(message)
            print(f"\n[handle_message]: proofreading emitted: {proofread_doc}")
            proofreading_sessions[user_id] = ""

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

        # conversations[user_id].display_conversation()

        message = json.dumps({"type": "endOfMessage", "data": ""})
        await websocket.send_text(message)


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

############################################################################################################
