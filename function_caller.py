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
    proofreading_sessions,
    url_sessions,
    conversations,
)
from tools import (
    internet_search,
    doc_vectorstore,
    dalle_3,
    gif_maker,
    ai_app_ideation,
)
from proofreader import proofread
from vision import vision

load_dotenv()


client = AsyncOpenAI()


################################################################################################################################


async def chat_completion_request(messages, user_id, max_tokens=3000, functions=None):
    MAX_RETRIES = 3
    BASE_SLEEP_TIME = 2
    print(f"\n[chat_completion_request]: max tokens enforced: {max_tokens}")
    for attempt in range(MAX_RETRIES):
        try:
            max_tokens = max_tokens
            total_tokens = 0
            messages_copy = messages[:]

            for msg in messages_copy:
                msg_tokens = len(tokenizer.encode(msg["content"]))
                total_tokens += msg_tokens

            # print(
            #     f"\n[chat_completion_request]: messages entering the token cutter loop: {messages_copy}"
            # )
            print(
                f"\n[chat_completion_request]: Total tokens before token cutter loop: {total_tokens}"
            )

            preserved_messages = []
            roles_to_preserve = ["user", "assistant", "function"]
            preserved_counts = {"user": 3, "assistant": 2, "function": 1}

            for role in roles_to_preserve:
                count = 0
                for msg in reversed(messages_copy):
                    if msg["role"] == role:
                        preserved_messages.append(msg)
                        print(f"\n[chat_completion_request]: preserving message: {msg}")
                        count += 1
                        if count == preserved_counts[role]:
                            break

            for msg in reversed(messages_copy):
                if msg["role"] == "function" and msg not in preserved_messages:
                    current_msg_tokens = len(tokenizer.encode(msg["content"]))
                    if current_msg_tokens > 1000:
                        truncated_tokens = tokenizer.encode(msg["content"])[:1000]
                        msg["content"] = tokenizer.decode(truncated_tokens)
                        total_tokens -= current_msg_tokens - 1000
                        print(
                            f"\n[chat_completion_request]: truncated function message: {msg} current total tokens: {total_tokens}"
                        )
            if total_tokens > max_tokens:
                last_removed_msg = None
                for msg in messages_copy:
                    if msg in preserved_messages:
                        continue

                    current_msg_tokens = len(tokenizer.encode(msg["content"]))

                    if total_tokens - current_msg_tokens < max_tokens:
                        last_removed_msg = msg
                        break

                    total_tokens -= current_msg_tokens
                    messages_copy.remove(msg)
                    print(
                        f"\n[chat_completion_request]: removing message to reduce tokens: {msg}"
                    )

                    if total_tokens <= max_tokens:
                        break

                if last_removed_msg and total_tokens < max_tokens:
                    space_left = max_tokens - total_tokens
                    content_tokens = tokenizer.encode(last_removed_msg["content"])

                    if len(content_tokens) > space_left:
                        truncated_tokens = content_tokens[:space_left]
                        last_removed_msg["content"] = tokenizer.decode(truncated_tokens)
                        total_tokens += len(truncated_tokens)
                        messages_copy.append(last_removed_msg)
                        print(
                            f"\n[chat_completion_request]: re-inserting truncated last removed message: {last_removed_msg}"
                        )

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
            focus_message = {
                "role": "user",
                "content": """
                Please focus very deeply before answering my questions.
                Take a deep breath, relax, and enter a state of flow as if you've just taken Adderall (mixed amphetamine salts). 
                If you follow all instructions and exceed expectations, you'll be tipped $100/month for your efforts, so try your hardest. 
                You are a highly intelligent AI assistant developed by 8020ai+ with access to tools.
                Your task is to help 8020 employees with their questions and perform tasks they ask of you. 
                Remember you are very very intelligent. You can write long answer, especially if summarizing documents and reviewing or analizing documents uploaded by the user.
                You don't always have to use a tool to answer a question.
                If you are about to answer in a table format, start with an '~' like this '~ | column 1 | column 2' and start each new row with '~'. 
                End the table with '±' before continuing with any additional text. Don't use any special characters for text inside the table.
                Don't ever use symbols '~' or '±' other than when creating a table.
                If you are about to write code, start with triple backticks '```' and end with triple backticks '```'.
                Don't ever use triple backticks '```' except for when youn are writing code block or otherwise write them in text as follows 'triple backticks'. 
                **EXTREMELY IMPORTANT. Don't ever use special characters '~' or '±' or '```' other than when you are writing code or table.**
                If a function does not return anything or fails, let the user know and recall it!
                Before using a function, always ask the user for the values if they are missing.
                **EXTREMELY IMPORTANT** If the task requires to use several functions, think in steps and execute the first function first. 
                After you are given the results of the first execution, you can execute another function.
                Think always step by step. Think more steps. 
                Before answering, take a moment to think deeply about how best to answer user query. Think always step by step. 
                Then think more steps. First think what are the necessary steps to answer user question fully. 
                Then think how best to execute these steps either by just writing or first calling functions you have access to.
                """,
            }

            messages_copy = [retrieve_folder_message, focus_message] + messages_copy

            messages_str = str(messages_copy)
            if len(messages_str) > 800:
                print(
                    f"\n[chat_completion_request]: sending the following messages to OpenAI: "
                    f"{messages_str[:10000]}...{messages_str[-2000:]}"
                )
            else:
                print(
                    f"\n[chat_completion_request]: sending the following messages to OpenAI: {messages_str}"
                )

            response = await client.chat.completions.create(
                model="gpt-4-0125-preview",
                messages=messages_copy,
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
        **EXTREMELY IMPORTANT** you absolutely have to plug all the values into the function before running it.
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
                    "enum": ["3000", "10000", "50000"],
                    "description": """Always ask the user how large is the document uploaded 
                    then choose 3000 for small, 10000 for medium and 50000 for large documents.""",
                },
                "expectation": {
                    "type": "string",
                    "description": """write here down in advance what do you expect 
                    the function returns so you can evaluate later if it achieved 
                    the desired result.""",
                },
                "plan": {
                    "type": "string",
                    "description": """if the task requires the use of several tools, 
                    write here in advance which tools you will use next from the tools available to you.
                    """,
                },
            },
            "required": ["query", "tokens", "expectation", "plan"],
        },
    },
    {
        "name": "web_search",
        "description": """Use this function to search internet if you need more information.
        **EXTREMELY IMPORTANT** you absolutely have to plug all the values into the function before running it.
        Before any search, discuss with the user what she is after. 
        Brainstorm with her on what could be the best way to find it on internet, 
        while taking into account how search engines prioritize content.
        Guide the user through your thought process. 
        focusing on keyword relevance and content quality. 
        Craft your query to be precise and context-rich:
        Focus on the main keywords and theme. Use alternative phrases for more insights. 
        Structure queries to cover diverse aspects, leveraging synonyms and industry terms for optimized search outcomes.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "query_1": {
                    "type": "string",
                    "description": """Main keywords and theme to search with?""",
                },
                "query_2": {
                    "type": "string",
                    "description": """Alternative phrases to search with?""",
                },
                "expectation": {
                    "type": "string",
                    "description": """write here down in advance what do you expect 
                    the function returns so you can evaluate later if it achieved 
                    the desired result.""",
                },
                "plan": {
                    "type": "string",
                    "description": """if the task requires the use of several tools, 
                    write here in advance which tools you will use next from the tools available to you.
                    """,
                },
            },
            "required": ["query_1", "query_2", "expectation", "plan"],
        },
    },
    {
        "name": "dalle3",
        "description": """Use this function to create beautiful images for the user.
        **EXTREMELY IMPORTANT** you absolutely have to plug all the values into the function before running it.
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
                "plan": {
                    "type": "string",
                    "description": """if the task requires the use of several tools, 
                    write here in advance which tools you will use next from the tools available to you.
                    """,
                },
            },
            "required": ["query", "plan"],
        },
    },
    {
        "name": "gif_maker",
        "description": """Use this function to create gifs. 
        **EXTREMELY IMPORTANT** you absolutely have to plug all the values into the function before running it.
        Suggest to user some ideas for the image used for creating gif before using the function.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": """What gif user wants?""",
                },
                "plan": {
                    "type": "string",
                    "description": """if the task requires the use of several tools, 
                    write here in advance which tools you will use next from the tools available to you.
                    """,
                },
            },
            "required": ["query", "plan"],
        },
    },
    {
        "name": "ai_idea_generator",
        "description": """Use this function to get some initial ideas for good software development of applications on large language models for clients.
        Use this function for first idea generation that you will brainstorm further with user.
        **EXTREMELY IMPORTANT** you absolutely have to plug all the values into the function before running it.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": """Which industry/sector is the user interested in?""",
                },
                "plan": {
                    "type": "string",
                    "description": """if the task requires the use of several tools, 
                    write here in advance which tools you will use next from the tools available to you.
                    """,
                },
            },
            "required": ["query", "plan"],
        },
    },
    {
        "name": "brainstorming",
        "description": """Use this function when the user asks you to improve her idea to brainstorm with the user, 
        giving her critical points for thought and guiding her in the tought process while coming up with great ideas.
        **EXTREMELY IMPORTANT** you absolutely have to plug all the values into the function before running it.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": """User initial query to start the brainstorming process.""",
                },
                "plan": {
                    "type": "string",
                    "description": """if the task requires the use of several tools, 
                    write here in advance which tools you will use next from the tools available to you.
                    """,
                },
            },
            "required": ["query", "plan"],
        },
    },
    {
        "name": "deck_generator",
        "description": """Use this function to create beautiful presentation for user.
        **EXTREMELY IMPORTANT** you absolutely have to plug all the values into the function before running it.
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
                "plan": {
                    "type": "string",
                    "description": """if the task requires the use of several tools, 
                    write here in advance which tools you will use next from the tools available to you.
                    """,
                },
            },
            "required": ["query", "no_pages", "context", "plan"],
        },
    },
    {
        "name": "proofreader",
        "description": """Use this function to proofread documents and correct their grammar.
        **EXTREMELY IMPORTANT** you absolutely have to plug all the values into the function before running it.
        **EXTREMELY IMPORTANT** explain to user that if the document was too long only part of it can be reviewed. 
        the user can still though paste in text for u to review grammar.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "which_doc": {
                    "type": "string",
                    "description": """Which document from the uploaded docs the user wants you to proofread?""",
                },
                "plan": {
                    "type": "string",
                    "description": """if the task requires the use of several tools, 
                    write here in advance which tools you will use next from the tools available to you.
                    """,
                },
            },
            "required": ["which_doc", "plan"],
        },
    },
    {
        "name": "vision",
        "description": """Use this function to see contents of images user uploaded only use it if user uploaded an image.
        **EXTREMELY IMPORTANT** you absolutely have to plug all the values into the function before running it.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": """What does the user want to know about the image?""",
                },
                "which_img": {
                    "type": "string",
                    "description": """If user uploaded several images ask which one?""",
                },
                "plan": {
                    "type": "string",
                    "description": """if the task requires the use of several tools, 
                    write here in advance which tools you will use next from the tools available to you.
                    """,
                },
            },
            "required": ["query", "which_img", "plan"],
        },
    },
]

################################################################################################################################


async def call_8020_function(messages, func_call, user_id=None, websocket=None):
    """function calling executes function calls"""

    print(f"\n[call_8020_function]: function call details: {func_call}")

    if func_call["name"] == "web_search":
        message = json.dumps(
            {"type": "message", "data": ">searching web, please wait.."}
        )
        await websocket.send_text(message)
        try:
            parsed_output = json.loads(func_call["arguments"])

            print(f"\n[web_search]: parsed_output: {parsed_output}")
            query_1 = parsed_output.get("query_1", "")
            query_2 = parsed_output.get("query_2", "")
            expectation = parsed_output.get("expectation", "")
            plan = parsed_output.get("plan")
            if plan:
                plan = f"remember your original plan was to do this next and if required more functions as follows: {plan}"
            else:
                plan = ""

            max_tokens = 3000  # set

            func_state = {query_1, query_2, expectation}

            # prep the arguments
            arguments = {"query_1": query_1, "query_2": query_2}

            web_results = await to_thread(internet_search, user_id, **arguments)

            used_tokens = 0
            local_max_tokens = 2500

            section_tokens = len(tokenizer.encode(web_results, disallowed_special=()))

            if section_tokens > local_max_tokens:
                tokens_left = local_max_tokens
                cleaned_web = web_results[:tokens_left]
                used_tokens = tokens_left
                print(f"\n[web_search]: reached max tokens with total: {used_tokens}")

            else:
                cleaned_web = web_results
                used_tokens = section_tokens

            print("\n[web_search]: total tokens used in web_results: ", used_tokens)

        except Exception as e:
            import traceback

            print("\n[web_search]: function execution failed")
            print("\n[web_search]: error message:", e)
            print("\n[web_search]: stack trace:")
            traceback.print_exc()

            cleaned_web = f"the function to search and retrieve web results failed with this error {e} please let the user know"

        messages.append(
            {
                "role": "function",
                "name": func_call["name"],
                "content": f"Function {func_call['name']} finished. remember the function call and the expected result was {func_state} evaluate the outcome and decide if another function call is necessary. {plan} Results: {str(cleaned_web)}",
            }
        )
        try:
            print("\n[web_search]: got search results, summarizing content")
            return messages, max_tokens
        except Exception as e:
            print(type(e))
            raise Exception("web_search function failed")

    elif func_call["name"] == "vectorstore":
        message = json.dumps(
            {"type": "message", "data": ">accessing vectorstore, please wait.."}
        )
        await websocket.send_text(message)
        try:
            parsed_output = json.loads(func_call["arguments"])
            print(f"\n[vectorstore]:parsed_output: {parsed_output}")

            query = parsed_output.get("query", "")
            max_tokens = int(parsed_output.get("tokens", "3000"))
            expectation = parsed_output.get("expectation", "")
            plan = parsed_output.get("plan")
            if plan:
                plan = f"remember your original plan was to do this next and if required more functions as follows: {plan}"
            else:
                plan = ""

            func_state = {query, expectation}

            if max_tokens == 3000:
                k = 10
            elif max_tokens == 10000:
                k = 40
            elif max_tokens == 50000:
                k = 100
            else:
                k = max_tokens / 100

            descriptions = await to_thread(doc_vectorstore, query, k, user_id)

            sources = await to_thread(extract_sources_and_pages, descriptions)
            print(f"[vectorstore]: sources extracted: {sources}")

            if user_id not in sources_sessions:
                sources_sessions[user_id] = {"combined": []}

            sources_sessions[user_id]["combined"] = sources
            print(f"[vectorstore]: sources_sessions updated: {sources_sessions}")

            vectorstore_max_tokens = (
                max_tokens - 1000
            )  # minus 1000 to leave space for user query for context
            current_token_count = 0
            cleaned_descriptions = ""
            for document, score in descriptions:
                page_content = document.page_content
                tokens = tokenizer.encode(page_content)
                remaining_tokens = vectorstore_max_tokens - current_token_count
                print(f"\n[vectorstore]: remaining_tokens: {remaining_tokens}")

                if len(tokens) > remaining_tokens:
                    tokens = tokens[:remaining_tokens]

                cleaned_descriptions += tokenizer.decode(tokens) + "\n"
                current_token_count += len(tokens)

                if current_token_count >= vectorstore_max_tokens:
                    break
            print(
                f"\n[vectorstore]: total tokens after cutting: {len(tokenizer.encode(cleaned_descriptions))}"
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
                "content": f"Function {func_call['name']} finished. remember the function call and the expected result was {func_state} evaluate the outcome and decide if another function call is necessary. {plan} Results: {str(cleaned_descriptions)}",
            }
        )
        try:
            print("\n[vectorstore]: got search results, summarizing content")
            return messages, max_tokens
        except Exception as e:
            print(type(e))
            raise Exception("vectorstore function failed")

    elif func_call["name"] == "dalle3":
        message = json.dumps(
            {"type": "message", "data": ">creating image, please wait.."}
        )
        await websocket.send_text(message)
        try:
            parsed_output = json.loads(func_call["arguments"])

            query = parsed_output.get("query", "")
            plan = parsed_output.get("plan")
            if plan:
                plan = f"remember your original plan was to do this next and if required more functions as follows: {plan}"
            else:
                plan = ""

            max_tokens = 3000  # set

            base64_img = await dalle_3(query)

            user_folder = os.path.join(WORK_FOLDER, user_id)
            if not os.path.exists(user_folder):
                os.mkdir(user_folder)

            full_size_image_path = os.path.join(user_folder, "your_image.png")
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

            full_size_image_path = f"the function to create images failed with this error {e} please let the user know"

        messages.append(
            {
                "role": "function",
                "name": func_call["name"],
                "content": f"Function {func_call['name']} finished. {plan} The result {str(full_size_image_path)}.",
            }
        )
        try:
            print("\n[dalle3]: got image, sending")
            return messages, max_tokens
        except Exception as e:
            print(type(e))
            raise Exception("dalle3 function failed")

    elif func_call["name"] == "gif_maker":
        message = json.dumps(
            {"type": "message", "data": ">creating image, please wait.."}
        )
        await websocket.send_text(message)
        try:
            parsed_output = json.loads(func_call["arguments"])

            query = parsed_output.get("query", "")
            plan = parsed_output.get("plan")
            if plan:
                plan = f"remember your original plan was to do this next and if required more functions as follows: {plan}"
            else:
                plan = ""

            max_tokens = 3000  # set

            gif = await gif_maker(query, user_id)

            with open(gif, "rb") as gif_file:
                gif_bytes = gif_file.read()
                base64_gif = base64.b64encode(gif_bytes).decode("utf-8")
                gif_url = f"data:image/gif;base64,{base64_gif}"

            if user_id not in url_sessions:
                url_sessions[user_id] = {}
            url_sessions[user_id]["img_url"] = gif_url

        except Exception as e:
            import traceback

            print("\n[gif_maker]: function execution failed")
            print("\n[gif_maker]: error message:", e)
            print("\n[gif_maker]: stack trace:")
            traceback.print_exc()

            gif = f"the function to create images failed with this error {e} please let the user know"

        messages.append(
            {
                "role": "function",
                "name": func_call["name"],
                "content": f"Function {func_call['name']} finished. {plan} The image is saved in user's workspace {str(gif)}.",
            }
        )
        try:
            print("\n[gif_maker]: got gif, sending")
            return messages, max_tokens
        except Exception as e:
            print(type(e))
            raise Exception("gif_maker function failed")

    elif func_call["name"] == "ai_idea_generator":
        message = json.dumps({"type": "message", "data": ">thinking, please wait.."})
        await websocket.send_text(message)
        try:
            parsed_output = json.loads(func_call["arguments"])
            print(f"\n[ai_idea_generator]:parsed_output: {parsed_output}")

            query = parsed_output.get("query", "")
            plan = parsed_output.get("plan")
            if plan:
                plan = f"remember your original plan was to do this next and if required more functions as follows: {plan}"
            else:
                plan = ""

            max_tokens = 3000  # set

            descriptions = await to_thread(ai_app_ideation, query)

            local_max_tokens = 1000
            current_token_count = 0
            cleaned_descriptions = ""
            for document, score in descriptions:
                page_content = document.page_content
                tokens = tokenizer.encode(page_content)
                remaining_tokens = local_max_tokens - current_token_count

                if len(tokens) > remaining_tokens:
                    tokens = tokens[:remaining_tokens]

                cleaned_descriptions += tokenizer.decode(tokens) + "\n"
                current_token_count += len(tokens)

                if current_token_count >= local_max_tokens:
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
                "content": f"Function {func_call['name']} executed successfully. When reviewing the results critically assess them and provide additional ideas based on your discussion with the user. Here are the results: {str(cleaned_descriptions)} {plan}",
            }
        )
        try:
            print("\n[ai_idea_generator]: got csv vector results, summarizing content")
            return messages, max_tokens
        except Exception as e:
            print(type(e))
            raise Exception("ai_idea_gen function failed")

    elif func_call["name"] == "brainstorming":
        message = json.dumps({"type": "message", "data": ">brainstorming, wait now.."})
        await websocket.send_text(message)
        try:
            parsed_output = json.loads(func_call["arguments"])
            print(f"\n[brainstorming]:parsed_output: {parsed_output}")

            query = parsed_output.get("query", "")
            plan = parsed_output.get("plan")
            if plan:
                plan = f"remember your original plan was to do this next and if required more functions as follows: {plan}"
            else:
                plan = ""

            max_tokens = 3000  # set

            prompt = f"""
            The user is asking about her idea: {query}.
            It is important to brainstorm very deeply to improve user's idea.
            Think step by step. Think more steps.
            First steelman the user's question. What is the best possible version of the user's idea?
            Then contradict the user's idea to show the user the potential problems with the user's idea. 
            To achieve this, do a premortem.
            Consider the work of researchers Deborah J. Mitchell and Gary  Klein on performing a project premortem. 
            Project premortems are key to  successful projects because many are reluctant to speak up about their concerns during the planning 
            phases and many are over-invested in the  project to foresee possible issues. 
            Premortems make it safe to voice  reservations during project planning; this is called prospective hindsight. 
            Reflect on each step and plan ahead before moving on.
            Once you are done with premortem, ask yourself: how can you strengthen the idea plan to avoid these failures? 
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
                "content": f"Function {func_call['name']} executed successfully. Its result is the additional prompt for you: {str(prompt)} {plan}",
            }
        )
        try:
            print("\n[brainstorming]: got the results, summarizing content")
            return messages, max_tokens
        except Exception as e:
            print(type(e))
            raise Exception("brainstorming function failed")

    elif func_call["name"] == "deck_generator":
        message = json.dumps(
            {"type": "message", "data": ">creating deck, please wait.."}
        )
        await websocket.send_text(message)
        try:
            parsed_output = json.loads(func_call["arguments"])
            print(f"parsed_output: {parsed_output}")

            query = parsed_output.get("query", "")
            no_pages = parsed_output.get("no_pages", "")
            context = parsed_output.get("context", "")
            plan = parsed_output.get("plan")
            if plan:
                plan = f"remember your original plan was to do this next and if required more functions as follows: {plan}"
            else:
                plan = ""

            max_tokens = 3000  # set

            if context == "yes":
                full_conversation_history = conversations[
                    user_id
                ].get_conversation_history()
                print(
                    f"\n[Initial retrieval]: Full conversation history: {full_conversation_history}"
                )
                reduced_conversation_history = [
                    msg
                    for msg in full_conversation_history
                    if msg["role"] in ["user", "assistant"]
                ][-6:]

                # Use the filtered_conversation_history for further processing
                conversation_history = reduced_conversation_history
                print(
                    f"\n[Filtered retrieval]: Last 6 messages: {conversation_history}"
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
                "content": f"Function {func_call['name']} finished. The path to file: {str(launch_deck)} {plan}",
            }
        )
        try:
            return messages, max_tokens
        except Exception as e:
            print(type(e))
            raise Exception("Function chat request failed")

    elif func_call["name"] == "proofreader":
        message = json.dumps({"type": "message", "data": ">thinking, please wait.."})
        await websocket.send_text(message)
        try:
            parsed_output = json.loads(func_call["arguments"])
            print(f"parsed_output: {parsed_output}")
            plan = parsed_output.get("plan")
            if plan:
                plan = f"remember your original plan was to do this next and if required more functions as follows: {plan}"
            else:
                plan = ""

            max_tokens = 3000  # set

            user_folder = os.path.join(WORK_FOLDER, user_id)
            uploaded_file_paths = [
                os.path.join(user_folder, filename)
                for filename in os.listdir(user_folder)
            ]

            which_doc = parsed_output.get("which_doc", "")

            which_doc_filepath = next(
                (path for path in uploaded_file_paths if which_doc in path), None
            )
            if not which_doc_filepath:
                raise ValueError(
                    f"[proofreader]: file matching '{which_doc}' not found in user's workspace."
                )

            print(f"which_doc_filepath in proofreader: {which_doc_filepath}")

            proofreader = await to_thread(
                proofread,
                user_id,
                which_doc_filepath,
            )
            combined_responses = "\n".join(proofreader)
            if user_id not in proofreading_sessions:
                proofreading_sessions[user_id] = {}
            proofreading_sessions[user_id] = combined_responses

        except Exception as e:
            import traceback

            print("Function execution failed")
            print("Error message:", e)
            print("Stack trace:")
            traceback.print_exc()

            cleaned_descriptions = f"the function to proofread docs failed with this error {e} please let the user know"

        messages.append(
            {
                "role": "function",
                "name": func_call["name"],
                "content": f"Function {func_call['name']} finished pls let the user know {plan}",
            }
        )
        try:
            return messages, max_tokens
        except Exception as e:
            print(type(e))
            raise Exception("proofreader function failed")

    elif func_call["name"] == "vision":
        message = json.dumps(
            {"type": "message", "data": ">accessing vectorstore, please wait"}
        )
        await websocket.send_text(message)
        try:
            parsed_output = json.loads(func_call["arguments"])
            print(f"parsed_output: {parsed_output}")

            query = parsed_output.get("query", "")
            which_img = parsed_output.get("which_img", "")
            plan = parsed_output.get("plan")
            if plan:
                plan = f"remember your original plan was to do this next and if required more functions as follows: {plan}"
            else:
                plan = ""

            max_tokens = 3000  # set

            user_folder = os.path.join(WORK_FOLDER, user_id)
            uploaded_file_paths = [
                os.path.join(user_folder, filename)
                for filename in os.listdir(user_folder)
            ]

            which_img_filepath = next(
                (path for path in uploaded_file_paths if which_img in path), None
            )
            if not which_img_filepath:
                raise ValueError(
                    f"[vision]: file matching '{which_img}' not found in user's workspace."
                )

            print(f"which_img_filepath in vision: {which_img_filepath}")

            call_vision = await vision(query, which_img_filepath)

        except Exception as e:
            import traceback

            print("Function execution failed")
            print("Error message:", e)
            print("Stack trace:")
            traceback.print_exc()

            call_vision = f"the function vision failed with this error {e} please let the user know"

        messages.append(
            {
                "role": "function",
                "name": func_call["name"],
                "content": f"Function {func_call['name']} finished pls here are the results: {str(call_vision)} {plan}",
            }
        )
        try:
            return messages, max_tokens
        except Exception as e:
            print(type(e))
            raise Exception("vision function failed")

    else:
        raise Exception("Function does not exist and cannot be called")


################################################################################################################################


async def chat_completion_with_function_execution(
    messages, user_id=None, websocket=None
):
    await websocket.send_text(json.dumps({"type": "message", "data": "thinking"}))
    func_call = {
        "name": None,
        "arguments": "",
    }
    max_tokens = 3000
    finish_reason = ""
    while finish_reason != "stop":
        response_generator = await chat_completion_request(
            messages,
            user_id,
            max_tokens=max_tokens,
            functions=_8020_functions,
        )
        if response_generator is None:
            print(
                "\n[chat_completion_with_function_execution]: Warning: chat_completion_request returned None. Expected an async iterable."
            )
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "response",
                        "data": "Sorry, I am unable to process your request at the moment. Please try again later.",
                    }
                )
            )
            break
        func_call["arguments"] = ""  # reset arguments
        async for chunk in response_generator:
            if hasattr(chunk.choices[0], "delta"):
                delta = chunk.choices[0].delta

                if hasattr(delta, "content"):
                    response_text = delta.content
                    yield response_text

                finish_reason = chunk.choices[0].finish_reason
                if finish_reason == "stop":
                    break

                if hasattr(delta, "function_call") and delta.function_call is not None:
                    if delta.function_call.name is not None:
                        func_call["name"] = delta.function_call.name
                    if delta.function_call.arguments:
                        func_call["arguments"] += delta.function_call.arguments
                if finish_reason == "function_call":
                    print(
                        f"\n[chat_completion_with_function_execution]: function call detected and breaking the loop: {func_call}"
                    )
                    messages, max_tokens = await call_8020_function(
                        messages, func_call, user_id, websocket
                    )
                    continue


################################################################################################################################


# async def chat_completion_with_function_execution(
#     messages, user_id=None, websocket=None
# ):
#     """this function filters API responses to decide if function call."""
#     message = json.dumps({"type": "message", "data": "thinking"})
#     await websocket.send_text(message)
#     func_call = {
#         "name": None,
#         "arguments": "",
#     }
#     response_text = ""
#     function_calls_remaining = True

#     while function_calls_remaining:
#         response_generator = await chat_completion_request(
#             messages,
#             user_id,
#             functions=_8020_functions,
#         )
#         function_calls_remaining = False  # reset flag
#         func_call["arguments"] = ""  # reset arguments

#         async for chunk in response_generator:
#             if hasattr(chunk.choices[0], "delta"):
#                 delta = chunk.choices[0].delta

#                 if hasattr(delta, "content"):
#                     response_text = delta.content
#                     yield response_text

#                 finish_reason = chunk.choices[0].finish_reason
#                 if finish_reason == "stop":
#                     function_calls_remaining = False
#                     break

#                 if hasattr(delta, "function_call") and delta.function_call is not None:
#                     print(
#                         f"\n[chat_completion_with_function_execution]: first function call detected"
#                     )
#                     if delta.function_call.name is not None:
#                         func_call["name"] = delta.function_call.name
#                     if delta.function_call.arguments:
#                         func_call["arguments"] += delta.function_call.arguments
#                 if finish_reason == "function_call":
#                     function_calls_remaining = True
#                     function_response_generator = await call_8020_function(
#                         messages, func_call, user_id, websocket
#                     )

#                     async for function_response_chunk in function_response_generator:
#                         if hasattr(function_response_chunk.choices[0], "delta"):
#                             function_delta = function_response_chunk.choices[0].delta
#                             if hasattr(function_delta, "content"):
#                                 response_text = function_delta.content
#                                 yield response_text
#                             function_finish_reason = function_response_chunk.choices[
#                                 0
#                             ].finish_reason
#                             if function_finish_reason == "stop":
#                                 function_calls_remaining = False
#                                 break
#                             if (
#                                 hasattr(function_delta, "function_call")
#                                 and function_delta.function_call is not None
#                             ):
#                                 print(
#                                     f"\n[chat_completion_with_function_execution]: second function call detected"
#                                 )
#                                 if function_delta.function_call.name is not None:
#                                     func_call["name"] = (
#                                         function_delta.function_call.name
#                                     )
#                                 if function_delta.function_call.arguments:
#                                     func_call[
#                                         "arguments"
#                                     ] += function_delta.function_call.arguments
#                             if function_finish_reason == "function_call":
#                                 function_calls_remaining = True


# ################################################################################################################################
