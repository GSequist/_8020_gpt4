"""please for any changes to code let me know thanks @george"""

import traceback
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings


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
            if which_doc_filepath:
                print(f"[doc_vectorstore]: inserting: {which_doc_filepath}")
                filter_param = dict(source=which_doc_filepath)
            else:
                print(
                    "[doc_vectorstore]: No specific filepath, running on entire vectorstore"
                )
                filter_param = {}

            retrieval = user_specific_db.similarity_search_with_score(
                query, k=20, filter=filter_param
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
