"""please for any changes to code let me know thanks @george"""

import json
import os
import time
from dotenv import load_dotenv
from openai import AsyncOpenAI
from termcolor import colored
import openai
from utils import tokenizer, WORK_FOLDER, extract_sources_and_pages, sources_sessions
from tools import (
    internet_search,
    doc_vectorstore,
)

load_dotenv()

client = AsyncOpenAI()


################################################################################################################################


async def chat_completion_request(messages, user_id, functions=None):
    MAX_RETRIES = 10
    BASE_SLEEP_TIME = 2
    for attempt in range(MAX_RETRIES):
        try:
            max_tokens = 3000
            total_tokens = 0

            for msg in messages:
                msg_content = msg["content"]
                msg_tokens = len(tokenizer.encode(msg_content, disallowed_special=()))
                total_tokens += msg_tokens

            print(
                f"\n[chat_completion_request]: total tokens before token cutter loop: {total_tokens}"
            )

            if total_tokens > max_tokens:
                tokens_to_remove = total_tokens - max_tokens
                last_msg = messages[-1]
                last_msg_content = last_msg["content"]
                last_msg_tokens = tokenizer.encode(last_msg_content)
                if len(last_msg_tokens) >= tokens_to_remove:
                    truncated_tokens = last_msg_tokens[:-tokens_to_remove]
                    last_msg["content"] = tokenizer.decode(truncated_tokens)
                    total_tokens = max_tokens

            print(
                f"\n[chat_completion_request]: total tokens after token cutter loop: {total_tokens}"
            )

            # a flag to check if user has uploaded files
            user_folder = os.path.join(WORK_FOLDER, user_id)
            uploaded_file_names = []

            if os.path.exists(user_folder):
                files = os.listdir(user_folder)
                if files:
                    uploaded_file_names.extend(files)  # adding file names to the list
                else:
                    uploaded_file_names.append("No files have been uploaded.")
            else:
                uploaded_file_names.append("No files have been uploaded.")

            retrieve_folder_message = {
                "role": "assistant",
                "content": f"So far the user has uploaded these files: {uploaded_file_names}.",
            }

            focus_message = {
                "role": "user",
                "content": """
                Please focus very deeply before answering my questions.
                Think always step by step.
                Think more steps. 
                You are a highly intelligent AI assistant developed by 8020ai+ with access to tools.
                Your task is to help 8020 employees with their questions and perform tasks they ask of you. 
                You don't always have to use a tool to answer a question.
                **NEVER make up information. USE FACTS ONLY.** 
                If a function does not return anything or fails, let the user know!
                If a function returns answer which is unsatisfactory given user's question, explain it to user and run the function again adjusting the parameters.
                Before answering, take a moment to think deeply about how best to answer user query and note your thoughts in the following format:
                |||Reasoning|||
                - Thought process here
                - Steps to answer
                |||Answer|||
                Then provide your answer below the scratchpad notes.
                """,
            }

            messages = [retrieve_folder_message, focus_message] + messages

            print(
                f"\n[chat_completion_request]: sending the following messages to OpenAI: {messages}"
            )

            response = await client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=messages,
                functions=functions,
                function_call="auto",
                stream=True,
            )
            print(f"\n[chat_completion_request]: got response from OpenAI: {response}")
            return response
        except openai.APIConnectionError as e:
            print(
                f"\n[chat_completion_request]: OpenAI APIConnectionError on attempt {attempt + 1}: {e}"
            )

            if attempt < MAX_RETRIES - 1:
                sleep_time = BASE_SLEEP_TIME * (2**attempt)  # exponential backoff
                print(
                    f"\n[chat_completion_request]: connection issue, waiting for {sleep_time} seconds before retrying..."
                )
                time.sleep(sleep_time)
            else:
                print(
                    f"\n[chat_completion_request]: failed to connect after {MAX_RETRIES} attempts. Not retrying anymore."
                )
                break

        except openai.APIError as e:
            print(
                f"\n[chat_completion_request]: OpenAI APIError on attempt {attempt + 1}: {str(e)}"
            )

            if attempt < MAX_RETRIES - 1:  # not the last attempt
                sleep_time = BASE_SLEEP_TIME * (2**attempt)  # exponential backoff
                print(
                    f"\n[chat_completion_request]: waiting for {sleep_time} seconds before retrying..."
                )
                time.sleep(sleep_time)
            else:
                print(
                    f"\n[chat_completion_request]: failed after {MAX_RETRIES} attempts. Not retrying anymore."
                )
                break

        except openai.error.InvalidRequestError as e:
            print(f"OpenAI InvalidRequestError: {e}")
            break

        except openai.RateLimitError as e:
            print(
                f"\n[chat_completion_request]: rate limit exceeded on attempt {attempt + 1}: {e}"
            )
            if attempt < MAX_RETRIES - 1:  # not the last attempt
                sleep_time = BASE_SLEEP_TIME * (2**attempt)  # exponential backoff
                print(f"Sleeping for {sleep_time} seconds before retrying...")
                time.sleep(sleep_time)
            else:
                print(
                    "\n[chat_completion_request]: failed after repeated rate limit errors. Not retrying anymore."
                )
                break

    # if we've reached here, all retry attempts have failed
    print(
        f"\n[chat_completion_request]: failed to get answer from OpenAI after {MAX_RETRIES} attempts"
    )
    return None


_8020_functions = [
    {
        "name": "vectorstore",
        "description": """Use this function to retrieve relevant sections of documents uploaded by user.
        Don't use the function without the values. ALWAYS, ask the user for the values if they are missing.  
        Ask the user to clarify their question. What area/type of internal processes their question relates to?
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": """What is user's question about the document? 
                    """,
                },
                "which_doc": {
                    "type": "string",
                    "description": "If user uploaded several documents which one is she asking questions about?",
                },
            },
            "required": ["query", "which_doc"],
        },
    },
    {
        "name": "duckduckgo_search",
        "description": """Use this function to search internet if you need more information.
        Don't use the function without the values. ALWAYS, ask the user for the values if they are missing.
        Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous.
        Remember never to include urls in your response. 
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": """What is the information the user is asking of you?""",
                },
            },
            "required": ["query"],
        },
    },
]


async def call_8020_function(messages, func_call, user_id=None, websocket=None):
    """function calling executes function calls"""

    print(f"\n[call_8020_function]: function call details: {func_call}")

    if func_call["name"] == "duckduckgo_search":
        message = json.dumps(
            {"type": "message", "data": ">searching web, please wait.."}
        )
        await websocket.send_text(message)
        try:
            parsed_output = json.loads(func_call["arguments"])

            print(f"\n[duckduckgo]: parsed_output: {parsed_output}")
            web_results = internet_search(parsed_output["query"])

            used_tokens = 0
            max_tokens = 2000

            section_tokens = len(tokenizer.encode(web_results, disallowed_special=()))

            if section_tokens > max_tokens:
                tokens_left = max_tokens
                cleaned_web = web_results[: tokens_left * 5]
                used_tokens = tokens_left
                print(f"\n[duckduckgo]: reached max tokens with total: {used_tokens}")

            else:
                cleaned_web = web_results
                used_tokens = section_tokens

            print("\n[duckduckgo]: total tokens used in web_results: ", used_tokens)

        except Exception as e:
            import traceback

            print("\n[duckduckgo]: function execution failed")
            print("\n[duckduckgo]: error message:", e)
            print("\n[duckduckgo]: stack trace:")
            traceback.print_exc()

            cleaned_web = f"the function to search and retrieve web results failed with this error {e} please let the user know"

        messages.append(
            {
                "role": "function",
                "name": func_call["name"],
                "content": f"Function {func_call['name']} executed successfully. Results: {str(cleaned_web)}",
            }
        )
        try:
            print("\n[duckduckgo]: got search results, summarizing content")
            response = await chat_completion_request(
                messages, user_id, functions=_8020_functions
            )
            return response
        except Exception as e:
            print(type(e))
            raise Exception("Function chat request failed")

    elif func_call["name"] == "vectorstore":
        message = json.dumps(
            {"type": "message", "data": ">accessing vectorstore, please wait.."}
        )
        await websocket.send_text(message)
        try:
            parsed_output = json.loads(func_call["arguments"])
            print(f"\n[vectorstore]:parsed_output: {parsed_output}")

            query = parsed_output.get("query", "")
            which_doc = parsed_output.get("which_doc", "")
            print(f"\n[vectorstore]:query: {query}")
            print(f"\n[vectorstore]:which_doc in doc_vectorstore: {which_doc}")

            user_folder = os.path.join(WORK_FOLDER, user_id)
            uploaded_file_paths = [
                os.path.join(user_folder, filename)
                for filename in os.listdir(user_folder)
            ]

            which_doc_filepath = next(
                (path for path in uploaded_file_paths if which_doc in path), None
            )
            if not which_doc_filepath:
                raise ValueError(
                    f"\n[vectorstore]: file matching '{which_doc}' not found in user's workspace."
                )

            print(f"which_doc_filepath in doc_vectorstore: {which_doc_filepath}")

            descriptions = doc_vectorstore(query, user_id, which_doc_filepath)

            sources = extract_sources_and_pages(descriptions)
            print(f"[vectorstore]: sources extracted: {sources}")

            # initiate sources_sessions dictionary:
            if user_id not in sources_sessions:
                sources_sessions[user_id] = {"combined": []}

            # store the combined sources and pages in the dictionary
            sources_sessions[user_id]["combined"] = sources
            print(f"[doc_vectorstore]: sources_sessions created: {sources_sessions}")

            max_tokens = 3000
            current_token_count = 0
            cleaned_descriptions = ""
            cleaned_descriptions = ""
            for document, score in descriptions:
                page_content = document.page_content
                tokens = tokenizer.encode(page_content)
                remaining_tokens = max_tokens - current_token_count

                if len(tokens) > remaining_tokens:
                    tokens = tokens[:remaining_tokens]

                cleaned_descriptions += tokenizer.decode(tokens) + "\n"
                current_token_count += len(tokens)

                if current_token_count >= max_tokens:
                    break
            print(f"\n[vectorstore]: Total tokens after cutting: {current_token_count}")

        except Exception as e:
            import traceback

            print("Function execution failed")
            print("Error message:", e)
            print("Stack trace:")
            traceback.print_exc()

            cleaned_descriptions = f"the function to search and retrieve documents failed with this error {e} please let the user know"

        messages.append(
            {
                "role": "function",
                "name": func_call["name"],
                "content": f"Function {func_call['name']} executed successfully. Results: {str(cleaned_descriptions)}",
            }
        )
        try:
            print("\n[vectorstore]: got search results, summarizing content")
            response = await chat_completion_request(
                messages, user_id, functions=_8020_functions
            )
            return response
        except Exception as e:
            print(type(e))
            raise Exception("Function chat request failed")

    else:
        raise Exception("Function does not exist and cannot be called")


async def chat_completion_with_function_execution(
    messages, user_id=None, websocket=None
):
    """this function filters API responses to decide if function call."""
    message = json.dumps({"type": "message", "data": "thinking"})
    await websocket.send_text(message)
    func_call = {
        "name": None,
        "arguments": "",
    }
    response_text = ""
    function_calls_remaining = True

    while function_calls_remaining:
        response_generator = await chat_completion_request(
            messages,
            user_id,
            functions=_8020_functions,
        )
        function_calls_remaining = False  # reset flag
        func_call["arguments"] = ""  # reset arguments

        async for chunk in response_generator:
            if hasattr(chunk.choices[0], "delta"):
                delta = chunk.choices[0].delta

                if hasattr(delta, "content"):
                    response_text = delta.content
                    yield response_text

                finish_reason = chunk.choices[0].finish_reason
                if finish_reason == "stop":
                    function_calls_remaining = False
                    break

                if hasattr(delta, "function_call") and delta.function_call is not None:
                    if delta.function_call.name is not None:
                        func_call["name"] = delta.function_call.name
                    if delta.function_call.arguments:
                        func_call["arguments"] += delta.function_call.arguments
                if finish_reason == "function_call":
                    function_calls_remaining = True
                    function_response_generator = await call_8020_function(
                        messages, func_call, user_id, websocket
                    )

                    async for function_response_chunk in function_response_generator:
                        if hasattr(function_response_chunk.choices[0], "delta"):
                            function_delta = function_response_chunk.choices[0].delta
                            if hasattr(function_delta, "content"):
                                response_text = function_delta.content
                                yield response_text
                            function_finish_reason = function_response_chunk.choices[
                                0
                            ].finish_reason
                            if function_finish_reason == "stop":
                                function_calls_remaining = False
                                break
                            if (
                                hasattr(function_delta, "function_call")
                                and function_delta.function_call is not None
                            ):
                                if function_delta.function_call.name is not None:
                                    func_call[
                                        "name"
                                    ] = function_delta.function_call.name
                                if function_delta.function_call.arguments:
                                    func_call[
                                        "arguments"
                                    ] += function_delta.function_call.arguments
                            if function_finish_reason == "function_call":
                                function_calls_remaining = True


################################################################################################################################
