"""please for any changes to code let me know thanks @george"""

import json
import base64
from PIL import Image
import io
import os
import time
from dotenv import load_dotenv
from openai import AsyncOpenAI
from asyncio import to_thread
import openai
from deck_generator import generate_prs
from utils import (
    tokenizer,
    WORK_FOLDER,
    extract_sources_and_pages,
    sources_sessions,
    url_sessions,
    conversations,
    Conversation,
)
from tools import (
    internet_search,
    doc_vectorstore,
    dalle_3,
    ai_app_ideation,
)

load_dotenv()


client = AsyncOpenAI()


################################################################################################################################


async def chat_completion_request(messages, user_id, max_tokens=3000, functions=None):
    MAX_RETRIES = 10
    BASE_SLEEP_TIME = 2
    print(f"\n[chat_completion_request]: max tokens enforced: {max_tokens}")
    for attempt in range(MAX_RETRIES):
        try:
            max_tokens = max_tokens
            total_tokens = 0
            last_removed_message = None

            for msg in messages:
                msg_content = msg["content"]
                msg_tokens = len(tokenizer.encode(msg_content))
                total_tokens += msg_tokens

            print(
                f"\n[chat_completion_request]: messages entering the token cutter loop: {messages}"
            )
            print(
                f"\n[chat_completion_request]: Total tokens before token cutter loop: {total_tokens}"
            )

            while total_tokens > max_tokens and messages:
                last_removed_message = messages.pop(0)
                removed_tokens = len(tokenizer.encode(last_removed_message["content"]))
                total_tokens -= removed_tokens

            if last_removed_message and total_tokens < max_tokens:
                remaining_tokens = max_tokens - total_tokens
                tokens = tokenizer.encode(last_removed_message["content"])

                truncated_tokens = tokens[:remaining_tokens]
                last_removed_message["content"] = tokenizer.decode(truncated_tokens)

                messages.insert(0, last_removed_message)
                total_tokens += len(truncated_tokens)

            print(
                f"\n[chat_completion_request]: Total tokens after token cutter loop: {total_tokens}"
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
            # if you are writing code always always start with special character ~ and end the code with another special character ~. Otherwise the code won't be shown to user.
            focus_message = {
                "role": "user",
                "content": """
                Please focus very deeply before answering my questions.
                You are a highly intelligent AI assistant developed by 8020ai+ with access to tools.
                Your task is to help 8020 employees with their questions and perform tasks they ask of you. 
                Remember you are very very intelligent.
                You don't always have to use a tool to answer a question.
                If you are about to answer in a table format, start with an '^' like this '^ | column 1 | column 2' and start each new row with '^'. End the table with '±' before continuing with any additional text. Don't use any special characters for text inside the table.
                Don't ever use symbols '^' or '±' other than when creating a table.
                If a function does not return anything or fails, let the user know!
                Before using a function, always ask the user for the values if they are missing.
                If a function returns answer which is unsatisfactory given user's question, explain it to user and run the function again adjusting the parameters. This is especially true for functions that return web results.
                Think always step by step.
                Think more steps. 
                Before answering, take a moment to think deeply about how best to answer user query and note your thoughts in the following format:
                |||logic|||
                - Thought process here
                - Steps to answer
                |||answer|||
                Then provide your answer below the scratchpad notes.
                """,
            }

            messages = [retrieve_folder_message, focus_message] + messages

            print(
                f"\n[chat_completion_request]: sending the following messages to OpenAI: {messages}"
            )

            response = await client.chat.completions.create(
                model="gpt-4-0125-preview",
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

        except openai.InvalidRequestError as e:
            print(f"\nOpenAI InvalidRequestError: {e}")
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


################################################################################################################################

_8020_functions = [
    {
        "name": "vectorstore",
        "description": """Use this function to retrieve relevant sections of documents uploaded by user.
        Ask the user to clarify their question before running the function. What area/type of information they are looking for  in the docs?
        Don't use the function without the values. ALWAYS, ask the user for the values if they are missing.
        Remember to always ask for the parameter tokens never make assumptions about the size of the document.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": """What is user's question about the document? 
                    """,
                },
                "tokens": {
                    "type": "string",
                    "enum": ["3000", "10000", "100000"],
                    "description": """Always ask the user how large is the document uploaded and 
                    how much she wants the AI to see. Small review is 3000 tokens, medium review is 10000 tokens, large review is 100000 tokens.""",
                },
            },
            "required": ["query", "tokens"],
        },
    },
    {
        "name": "duckduckgo_search",
        "description": """Use this function to search internet if you need more information.
        If the function does not return satisfying results, explain it to the user and run the function again adjusting the parameters.
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
    {
        "name": "dalle3",
        "description": """Use this function to create beautiful images for the user.
        Remember to explain to the user that the more descriptive she is the better the image. 
        Suggest to user some ideas for the image before using the function.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": """What image user wants?""",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "ai_idea_generator",
        "description": """Use this function to get some initial ideas for good software development of applications on large language models for clients.
        Use this function for first idea generation that you will brainstorm further with user.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": """Which industry/sector is the user interested in?""",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "brainstorming",
        "description": """Use this function when the user asks you to improve her idea to brainstorm with the user, giving her critical points for thought and guiding her in the tought process while coming up with great ideas.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": """User initial query to start the brainstorming process.""",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "deck_generator",
        "description": """Use this function to create beautiful presentation for user.
        Always ask user as many details as possible to be able to create the presentation.
        Ask the user for number of slides minimum is 3 and maximum 5 so she does not wait long.
        Always ask if she wants to use the context or information from your previous discussion to be used in the slides.
        If the user does not provide all values ask again until you have all values.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": """What should the presentation be about?""",
                },
                "no_pages": {
                    "type": "string",
                    "enum": ["3", "4", "5"],
                    "description": """How many slides the user wants?""",
                },
                "context": {
                    "type": "string",
                    "enum": ["yes", ""],
                    "description": """Does the user want you to wants to use the information from your previous discussion.""",
                },
            },
            "required": ["query", "no_pages", "context"],
        },
    },
]

################################################################################################################################


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
            web_results = await to_thread(internet_search, parsed_output["query"])

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
            print(f"\n[vectorstore]:query: {query}")
            max_tokens = int(parsed_output.get("tokens", "3000"))
            print(f"\n[vectorstore]:tokens: {max_tokens}")

            if max_tokens == 3000:
                k = 10
            elif max_tokens == 10000:
                k = 40
            elif max_tokens == 100000:
                k = 120
            else:
                k = max_tokens / 100

            descriptions = await to_thread(doc_vectorstore, query, k, user_id)

            sources = await to_thread(extract_sources_and_pages, descriptions)
            print(f"[vectorstore]: sources extracted: {sources}")

            # initiate sources_sessions dictionary:
            if user_id not in sources_sessions:
                sources_sessions[user_id] = {"combined": []}

            # store the combined sources and pages in the dictionary
            sources_sessions[user_id]["combined"] = sources
            print(f"[vectorstore]: sources_sessions updated: {sources_sessions}")

            max_tokens = max_tokens
            current_token_count = 0
            cleaned_descriptions = ""
            for document, score in descriptions:
                page_content = document.page_content
                tokens = tokenizer.encode(page_content)
                remaining_tokens = max_tokens - current_token_count
                print(f"[vectorstore]: remaining_tokens: {remaining_tokens}")

                if len(tokens) > remaining_tokens:
                    tokens = tokens[:remaining_tokens]

                cleaned_descriptions += tokenizer.decode(tokens) + "\n"
                current_token_count += len(tokens)

                if current_token_count >= max_tokens:
                    break
            print(
                f"\n[vectorstore]: Total tokens after cutting: {len(tokenizer.encode(cleaned_descriptions))}"
            )

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
                messages, user_id, max_tokens=max_tokens, functions=_8020_functions
            )
            return response
        except Exception as e:
            print(type(e))
            raise Exception("Function chat request failed")

    elif func_call["name"] == "dalle3":
        message = json.dumps(
            {"type": "message", "data": ">creating image, please wait.."}
        )
        await websocket.send_text(message)
        try:
            parsed_output = json.loads(func_call["arguments"])

            query = parsed_output.get("query", "")
            print(f"\n[dalle3]:query: {query}")

            base64_img = await dalle_3(query)

            user_folder = os.path.join(WORK_FOLDER, user_id)
            if not os.path.exists(user_folder):
                os.mkdir(user_folder)

            full_size_image_path = os.path.join(user_folder, "dalle3.png")
            with open(full_size_image_path, "wb") as file:
                file.write(base64_img)

            image = Image.open(io.BytesIO(base64_img))
            image.thumbnail((512, 512))
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            resized_base64_img = base64.b64encode(buffered.getvalue()).decode()

            base64_url = f"data:image/png;base64,{resized_base64_img}"

            if user_id not in url_sessions:
                url_sessions[user_id] = {}
            url_sessions[user_id]["img_url"] = base64_url

        except Exception as e:
            import traceback

            print("\n[dalle3]: function execution failed")
            print("\n[dalle3]: error message:", e)
            print("\n[dalle3]: stack trace:")
            traceback.print_exc()

            cleaned_web = f"the function to create images failed with this error {e} please let the user know"

        messages.append(
            {
                "role": "function",
                "name": func_call["name"],
                "content": f"Function {func_call['name']} executed successfully. The image is saved in user's workspace {full_size_image_path}.",
            }
        )
        try:
            print("\n[dalle3]: got image, sending")
            response = await chat_completion_request(
                messages, user_id, functions=_8020_functions
            )
            return response
        except Exception as e:
            print(type(e))
            raise Exception("Function chat request failed")

    elif func_call["name"] == "ai_idea_generator":
        message = json.dumps({"type": "message", "data": ">thinking, please wait.."})
        await websocket.send_text(message)
        try:
            parsed_output = json.loads(func_call["arguments"])
            print(f"\n[ai_idea_generator]:parsed_output: {parsed_output}")

            query = parsed_output.get("query", "")
            print(f"\n[ai_idea_generator]:query: {query}")

            descriptions = await to_thread(ai_app_ideation, query)

            max_tokens = 1000
            current_token_count = 0
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
            print(
                f"\n[ai_idea_generator]: Total tokens after cutting: {current_token_count}"
            )

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
                "content": f"Function {func_call['name']} executed successfully. When reviewing the results critically assess them and provide additional ideas based on your discussion with the user. Here are the results: {str(cleaned_descriptions)}",
            }
        )
        try:
            print("\n[ai_idea_generator]: got csv vector results, summarizing content")
            response = await chat_completion_request(
                messages, user_id, functions=_8020_functions
            )
            return response
        except Exception as e:
            print(type(e))
            raise Exception("Function chat request failed")

    elif func_call["name"] == "brainstorming":
        message = json.dumps({"type": "message", "data": ">brainstorming, wait now.."})
        await websocket.send_text(message)
        try:
            parsed_output = json.loads(func_call["arguments"])
            print(f"\n[brainstorming]:parsed_output: {parsed_output}")

            query = parsed_output.get("query", "")
            print(f"\n[brainstorming]:query: {query}")

            prompt = f"""
            The user is asking about her idea: {query}.
            It is important to brainstorm very deeply to the improve user's idea.
            Think step by step. Think more steps.
            First steelman the user's question. What is the best possible version of the user's idea?
            Then contradict the user's idea to show the user the potential problems with the user's idea.
            Then propose improved ideas to the user.
            Then propose ideas based on the constraints you have identified above.
            Finally assess the ideas you have come up with based on feasibility, impact and originality in a table format.
            """

        except Exception as e:
            import traceback

            print("Function execution failed")
            print("Error message:", e)
            print("Stack trace:")
            traceback.print_exc()

            prompt = f"the function to brainstorming failed with this error {e} please let the user know"

        messages.append(
            {
                "role": "function",
                "name": func_call["name"],
                "content": f"Function {func_call['name']} executed successfully. Its result is the additional prompt for you: {str(prompt)}",
            }
        )
        try:
            print("\n[brainstorming]: got the results, summarizing content")
            response = await chat_completion_request(
                messages, user_id, functions=_8020_functions
            )
            return response
        except Exception as e:
            print(type(e))
            raise Exception("Function chat request failed")

    elif func_call["name"] == "deck_generator":
        message = json.dumps(
            {"type": "message", "data": ">creating deck, please wait.."}
        )
        await websocket.send_text(message)
        try:
            parsed_output = json.loads(func_call["arguments"])
            print(f"parsed_output: {parsed_output}")

            query = parsed_output["query"]
            no_pages = parsed_output["no_pages"]
            context = parsed_output["context"]

            if context == "yes":
                conversation_history = conversations[user_id].get_conversation_history()
                print(
                    f"\n[deck_generator]: conversation_history retrieved: {conversation_history}"
                )
            else:
                conversation_history = None

            launch_deck = await to_thread(
                generate_prs,
                user_id,
                query,
                no_pages,
                context=conversation_history,
            )

        except Exception as e:
            import traceback

            print("Function execution failed")
            print("Error message:", e)
            print("Stack trace:")
            traceback.print_exc()

            cleaned_descriptions = f"the function to create presentation failed with this error {e} please let the user know"

        messages.append(
            {
                "role": "function",
                "name": func_call["name"],
                "content": f"Function {func_call['name']} executed successfully. The path to file: {str(launch_deck)}",
            }
        )
        try:
            response = await chat_completion_request(
                messages, user_id, functions=_8020_functions
            )
            return response
        except Exception as e:
            print(type(e))
            raise Exception("Function chat request failed")

    else:
        raise Exception("Function does not exist and cannot be called")


################################################################################################################################


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
                ##helper
                # print(f"\n[chat_completion_with_function_execution]: chunk: {chunk}")
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
