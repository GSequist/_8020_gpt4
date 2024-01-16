"""please for any changes to code let me know thanks @george"""

import traceback
import base64
from dotenv import load_dotenv
from openai import AsyncOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain_community.document_loaders import CSVLoader

load_dotenv()

client = AsyncOpenAI()

#############################################################################################################
# doc_vectorstore


def doc_vectorstore(query: str, user_id: str, which_doc_filepath: str = None) -> str:
    """vectorstore the uploaded docs"""
    try:
        user_faiss_filename = f"faiss_db_{user_id}"

        embeddings = OpenAIEmbeddings()
        user_specific_db = FAISS.load_local(user_faiss_filename, embeddings)
        print(f"[doc_vectorstore]: FAISS index loaded for user {user_id}")

        if user_specific_db:
            retrieval = user_specific_db.similarity_search_with_score(
                query,
                k=20,
            )
            # sort by score
            sorted_retrieval = sorted(retrieval, key=lambda x: x[1], reverse=True)
            print(
                f"[doc_vectorstore]: vectorstore retrieval sorted: {sorted_retrieval}"
            )
            return sorted_retrieval

        # no user_db faiss found or other error
        return

    except Exception as e:
        print(f"error in doc_vectorstore: {e}")
        return


#####################################################################################################
## web search


def internet_search(query):
    """search the internet dynamically based on user interaction"""
    print(f"Initiating internet search for query: {query}")
    try:
        search = DuckDuckGoSearchRun()
        results = search.run(query)
        print(f"[duckduckgo]: web search results: {results}")
        return results
    except Exception as e:
        tb = traceback.format_exc()


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
