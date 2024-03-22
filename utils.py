"""please for any changes to code let me know thanks @george"""

import tiktoken
import os
import re
import uuid
from termcolor import colored


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
proofreading_sessions = {}
audio_preferences = {}

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
    def __init__(self, max_length=50):
        """holds the conversation loop"""
        self.conversation_history = []
        self.max_length = max_length

    def add_message(self, role, content):
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

    def delete_conversation(self):
        self.conversation_history = []
        print("\n[Conversation]: Conversation history deleted.")

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
        """Abbreviates function messages in the conversation history containing image data."""
        image_data_pattern = re.compile(r"data:image/.*?;base64,")

        for message in self.conversation_history:
            if message["role"] == "function":
                if image_data_pattern.search(message["content"]):
                    abbreviation_note = "\n[Image data abbreviated for brevity]"
                    message["content"] = "[Binary Data: Image]" + abbreviation_note


############################################################################################################
