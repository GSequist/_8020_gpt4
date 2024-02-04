"""please for any changes to code let me know thanks @george"""

import tiktoken
import os
import re
import uuid
from termcolor import colored


############################################################################################################
# ##define user ID
def generate_user_id():
    return uuid.uuid4().hex


##request userID from front-end
def get_current_user_id(request_user_id):
    if request_user_id is None:
        request_user_id = generate_user_id()
    return request_user_id


############################################################################################################
##tokenizer

tokenizer = tiktoken.get_encoding("cl100k_base")

############################################################################################################
##sessions

url_sessions = {}
sources_url_sessions = {}
sources_sessions = {}
user_sessions = {}
conversations = {}

############################################################################################################
## work folder

WORK_FOLDER = "workspace/"


############################################################################################################
##extract sources


def extract_sources_and_pages(results):
    print(f"Extracting sources and pages from results")
    sources_and_pages = []

    try:
        for result in results:
            full_source = result[0].metadata.get("source", None)
            page = result[0].metadata.get("page", None)
            source_filename = os.path.basename(full_source)

            if source_filename and page is not None:
                combined = f"{source_filename}\nPage: {page}"
                sources_and_pages.append(combined)
            else:
                print(
                    f"\n[extract_sources_and_pages]: source or page not found in content"
                )
    except Exception as e:
        print(f"\n[extract_sources_and_pages]: error: {e}")
        return None
    return sources_and_pages


############################################################################################################
##class conversation


class Conversation:
    def __init__(
        self, max_length=50
    ):  # if an average message is around 100 characters long (which might be a reasonable estimate for a chat-based interface, though the real number could be higher or lower depending on your specific use case), 50 messages would mean around 5,000 characters of text, or about 5KB of memory.
        self.conversation_history = []
        self.max_length = max_length

    def add_message(self, role, content):
        approx_token_length = len(content) // 5
        if approx_token_length > 1000:
            content = content[: 1000 * 5]

        message = {"role": role, "content": content}
        if len(self.conversation_history) >= self.max_length:
            self.conversation_history.pop(0)
        self.conversation_history.append(message)

    def display_conversation(self, detailed=False):
        role_to_color = {
            "system": "red",
            "user": "green",
            "assistant": "blue",
            "function": "magenta",
            "code": "yellow",
        }
        for message in self.conversation_history:
            print(
                colored(
                    f"{message['role']}: {message['content']}\n",
                    role_to_color[message["role"]],
                )
            )

    def get_conversation_history(self):
        """
        Prepares the conversation history for sending to the frontend.
        Returns a JSON string of the conversation history.
        """
        filtered_history = [
            msg
            for msg in self.conversation_history
            if msg["role"] in ["user", "assistant"]
        ]
        return filtered_history

    def abbreviate_function_messages(self):
        """Abbreviates function messages in the conversation history"""

        for message in self.conversation_history:
            if message["role"] == "function":
                is_binary_data = "data:image/jpeg;base64," in message["content"]
                if is_binary_data:
                    abbreviation_note = "\n[Image data abbreviated for brevity]"
                    message["content"] = "[Binary Data: Image]" + abbreviation_note
                match = re.search(
                    r"(Function .+? Results:)([\s\S]*?)(?=(assistant:|user:|system:|function:|$))",
                    message["content"],
                )
                if match:
                    result_words = match.group(2).split()[:2000]
                    short_result = " ".join(result_words)
                    abbreviation_note = (
                        "\n[Large result from vectorstore abbreviated for brevity]"
                    )
                    message["content"] = (
                        match.group(1) + short_result + abbreviation_note
                    )


############################################################################################################
