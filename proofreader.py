from dotenv import load_dotenv
from ingest import GLOBAL_CHUNKED_TEXTS
from typing import List
from openai import OpenAI
import openai
import traceback
import time
from utils import proofreading_sessions


load_dotenv()

client = OpenAI()


def proofread(user_id: str, which_doc_filepath: str) -> List[str]:

    if user_id not in GLOBAL_CHUNKED_TEXTS:
        print(f"\n[proofread]: no chunks found for user_id: {user_id}")
        return

    print(f"\n[proofread]: extracting chunks for filepath: {which_doc_filepath}")
    chunks = [
        chunk.page_content
        for chunk in GLOBAL_CHUNKED_TEXTS[user_id]
        if chunk.metadata.get("source") == which_doc_filepath
    ][:5]
    print(f"\n[proofread]: extracted {len(chunks)} chunks for proofreading")

    responses = []
    for chunk in chunks:
        try:
            result = call_gpt4(chunk)
            responses.append(result)
            print(f"[proofread]: completed processing of chunk.")
        except Exception as e:
            print(
                f"[proofread]: Error processing chunk: {e}\n",
                traceback.format_exc(),
            )

    print(f"[proofread]: Completed processing of all  chunks.")
    return responses


MAX_RETRIES = 10
BASE_SLEEP_TIME = 2


def call_gpt4(chunk):
    for attempt in range(MAX_RETRIES):
        print(f"\n[call_gpt4]: sending LLM the following chunk to proffread: {chunk}")
        try:
            response = client.chat.completions.create(
                model="gpt-4-0125-preview",
                messages=[
                    {
                        "role": "user",
                        "content": f"before you begin take a deep breath and focus very deeply. Review this text and proofread it word by word and correct it show me only the sections that need correcting and your corrections. Remember to ignore spacing errors as this could be due to how text was loaded. If you dont find anything to correctm it is ok to say so. First in steps first find text that need correcting then write down the correct text. Do not change the meaning of the text. \n"
                        + chunk,
                    }
                ],
            )

            return response.choices[0].message.content

        except openai.APIConnectionError as e:
            print(
                f"\n[call_gpt4]: OpenAI APIConnectionError on attempt {attempt + 1}: {e}"
            )

            if attempt < MAX_RETRIES - 1:
                sleep_time = BASE_SLEEP_TIME * (2**attempt)  # exponential backoff
                print(
                    f"\n[call_gpt4]: connection issue, waiting for {sleep_time} seconds before retrying..."
                )
                time.sleep(sleep_time)
            else:
                print(
                    f"\n[call_gpt4]: failed to connect after {MAX_RETRIES} attempts. Not retrying anymore."
                )
                break

        except openai.APIError as e:
            print(f"\n[call_gpt4]: OpenAI APIError on attempt {attempt + 1}: {str(e)}")

            if attempt < MAX_RETRIES - 1:  # not the last attempt
                sleep_time = BASE_SLEEP_TIME * (2**attempt)  # exponential backoff
                print(
                    f"\n[call_gpt4]: waiting for {sleep_time} seconds before retrying..."
                )
                time.sleep(sleep_time)
            else:
                print(
                    f"\n[call_gpt4]: failed after {MAX_RETRIES} attempts. Not retrying anymore."
                )
                break

        except openai.InvalidRequestError as e:
            print(f"\n[call_gpt4]: OpenAI InvalidRequestError: {e}")
            break

        except openai.RateLimitError as e:
            print(f"\n[call_gpt4]: rate limit exceeded on attempt {attempt + 1}: {e}")
            if attempt < MAX_RETRIES - 1:  # not the last attempt
                sleep_time = BASE_SLEEP_TIME * (2**attempt)  # exponential backoff
                print(
                    f"\n[call_gpt4]: sleeping for {sleep_time} seconds before retrying..."
                )
                time.sleep(sleep_time)
            else:
                print(
                    "\n[call_gpt4]: failed after repeated rate limit errors. Not retrying anymore."
                )
                break

    # all retry attempts have failed
    failure_message = (
        f"\n[call_gpt4]: failed to get answer from OpenAI after {MAX_RETRIES} attempts"
    )
    print(failure_message)
    return failure_message


#####################################################################################################
