"""please for any changes to code let me know thanks @george"""

import traceback
import base64
import re
from PIL import Image, ImageSequence
import numpy as np
import os
from utils import sources_url_sessions, WORK_FOLDER
from dotenv import load_dotenv
from openai import AsyncOpenAI
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import CSVLoader

load_dotenv()

client = AsyncOpenAI()

#############################################################################################################
# doc_vectorstore


def doc_vectorstore(query: str, k, user_id: str) -> str:
    """vectorstore the uploaded docs"""
    try:
        user_faiss_filename = f"faiss_db_{user_id}"
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        user_specific_db = FAISS.load_local(user_faiss_filename, embeddings)
        print(f"[doc_vectorstore]: FAISS index loaded for user {user_id}")
        if user_specific_db:
            retrieval = user_specific_db.similarity_search_with_score(
                query,
                k=k,
            )
            sorted_retrieval = sorted(retrieval, key=lambda x: x[1])
            print(
                f"[doc_vectorstore]: vectorstore retrieval sorted: {sorted_retrieval}"
            )
            return sorted_retrieval
        return
    except Exception as e:
        print(f"error in doc_vectorstore: {e}")
        return


#####################################################################################################
## web search


def internet_search(user_id, query_1, query_2):
    """search the internet dynamically for multiple queries"""
    all_results = []
    for query in [query_1, query_2]:
        if query is None:
            continue
        print(f"\nInitiating internet search for query: {query}")
        try:
            wrapper = DuckDuckGoSearchAPIWrapper(max_results=1)
            search = DuckDuckGoSearchResults(api_wrapper=wrapper)
            results = search.run(query)
            print(f"\n[internet_search]: web search results for '{query}': {results}")
            try:
                source_link = extract_links(results)
                print(f"\n[internet_search]: source link: {source_link}")
                if user_id not in sources_url_sessions:
                    sources_url_sessions[user_id] = {}
                sources_url_sessions[user_id]["sources_url"] = source_link
            except Exception as e:
                source_link = None
            if source_link:
                try:
                    fetch = web_fetch(query, source_link) if source_link else None
                except Exception as e:
                    fetch = None
            result_str = (
                f"Query: {query}\nSearch Results: {results}\nFetch Results: {fetch}\n"
            )
            all_results.append(result_str)
        except Exception as e:
            tb = traceback.format_exc()
            error_message = f"Query: {query}\nError: An error occurred during search.\nTraceback: {tb}\n"
            all_results.append(error_message)
        print(f"\n[internet_search]: all results: {all_results}")
    return "\n".join(all_results)


def extract_links(results):
    url_pattern = r"link: (\S+)"
    match = re.search(url_pattern, results)
    if match:
        link = match.group(1)
        cleaned_link = link.replace("[", "").replace("]", "").replace(",", "").strip()
        return cleaned_link
    else:
        return None


def web_fetch(query, url):
    """fetch the web contents"""
    web_text_loader = WebBaseLoader(url)
    web_text = web_text_loader.load()
    print(f"\n[web_fetch]: web text loaded {web_text}")
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    web_text_cuts = text_splitter.split_documents(web_text)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    try:
        web_faiss = FAISS.from_documents(web_text_cuts, embeddings)
        print(f"\n[web_fetch]: FAISS index loaded for web content")
        retrieval = web_faiss.similarity_search_with_score(
            query,
            k=2,
        )
        print(f"\n[web_fetch]: vectorstore retrieval: {retrieval}")
        sorted_retrieval = sorted(retrieval, key=lambda x: x[1], reverse=True)
        print(f"\n[web_fetch]: vectorstore retrieval sorted: {sorted_retrieval}")
        return sorted_retrieval
    except Exception as e:
        print(f"error in web_fetch: {e}")
        return


#####################################################################################################
## dalle3


async def dalle_3(query: str):
    image_response = await client.images.generate(
        model="dall-e-3",
        prompt=query,
        n=1,
        size="1024x1024",
        response_format="b64_json",
    )

    return base64.b64decode(image_response.data[0].b64_json)


#####################################################################################################
## gif maker


async def gif_maker(query: str, user_id: str):
    image_response = await client.images.generate(
        model="dall-e-3",
        prompt=f"create a sprite sheet WITH ONLY ONE ROW OF SPRITES of a {query} remember the image will be later converted to a gif by dividing into frames horizontally and there must be only one row of sprites.",
        n=1,
        size="1024x1024",
        response_format="b64_json",
    )

    base64_img = base64.b64decode(image_response.data[0].b64_json)

    user_folder = os.path.join(WORK_FOLDER, user_id)
    if not os.path.exists(user_folder):
        os.mkdir(user_folder)
    full_size_image_path = os.path.join(user_folder, "image.png")
    with open(full_size_image_path, "wb") as file:
        file.write(base64_img)

    sprite_sheet = Image.open(full_size_image_path)
    num_frames = 6
    sprite_width = sprite_sheet.width // num_frames
    sprite_height = sprite_sheet.height

    frames = []
    for i in range(num_frames):
        frame = sprite_sheet.crop(
            (i * sprite_width, 0, (i + 1) * sprite_width, sprite_height)
        )
        frames.append(frame)

    gif_path = os.path.join(user_folder, "your_gif.gif")
    frames[0].save(
        gif_path, save_all=True, append_images=frames[1:], duration=100, loop=0
    )

    return gif_path


#####################################################################################################
## AI app ideation
def ai_app_ideation(query: str):
    """generate app ideas based on user query"""
    loader = CSVLoader(
        file_path="8020ai+industry_selector/industry_selector.csv",
        csv_args={"delimiter": ","},
        encoding="utf-8",
    )
    data = loader.load()
    embeddings = OpenAIEmbeddings()
    db = FAISS.from_documents(data, embeddings)
    retrieval = db.similarity_search_with_score(query, k=10)
    sorted_retrieval = sorted(retrieval, key=lambda x: x[1], reverse=True)
    return sorted_retrieval
