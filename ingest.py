import os
import shutil
import glob
from typing import List
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import (
    CSVLoader,
    EverNoteLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredEmailLoader,
    UnstructuredEPubLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader,
    UnstructuredODTLoader,
    UnstructuredPowerPointLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredExcelLoader,
)

#############################################################################################################
## master loader of all document types

# map file extensions to document loaders and their arguments
LOADER_MAPPING = {
    ".csv": (CSVLoader, {}),
    ".xls": (UnstructuredExcelLoader, {}),
    ".xlsx": (UnstructuredExcelLoader, {}),
    ".doc": (UnstructuredWordDocumentLoader, {}),
    ".docx": (UnstructuredWordDocumentLoader, {}),
    ".enex": (EverNoteLoader, {}),
    ".eml": (UnstructuredEmailLoader, {}),
    ".epub": (UnstructuredEPubLoader, {}),
    ".html": (UnstructuredHTMLLoader, {}),
    ".md": (UnstructuredMarkdownLoader, {}),
    ".odt": (UnstructuredODTLoader, {}),
    ".pdf": (PyPDFLoader, {}),
    ".ppt": (UnstructuredPowerPointLoader, {}),
    ".pptx": (UnstructuredPowerPointLoader, {}),
    ".txt": (TextLoader, {}),
}

GLOBAL_CHUNKED_TEXTS = {}
GLOBAL_FAISS_DBs = {}


def load_single_document(file_path: str) -> List[Document]:
    original_file_path = file_path
    ext = "." + file_path.rsplit(".", 1)[-1]
    if ext in LOADER_MAPPING:
        loader_class, loader_args = LOADER_MAPPING[ext]
        loader = loader_class(file_path, **loader_args)
        try:
            print(f"[load_single_document]: loading {file_path}")
            documents = loader.load()
            if original_file_path != file_path:
                os.remove(original_file_path)
            return documents
        except Exception as e:
            os.remove(file_path)
            print(f"error processing {file_path}. Reason: {e}. File removed.")
            return []
    else:
        raise ValueError(f"[load_single_document]: unsupported file extension '{ext}'")


def load_documents(source_dir: str) -> List[Document]:
    all_files = []
    for ext in LOADER_MAPPING:
        all_files.extend(
            glob.glob(os.path.join(source_dir, f"**/*{ext}"), recursive=True)
        )
    all_data = []
    for file in all_files:
        docs = load_single_document(file)
        all_data.extend(docs)
    print(
        f"[load_documents]: Loaded a total of {len(all_data)} documents from {source_dir}"
    )

    return all_data


def process_documents(user_id: str, user_folder: str) -> None:
    """
    load documents, split in chunks for each user
    """
    try:
        print(f"[process_documents]: loading documents from {user_folder}")
        documents = load_documents(user_folder)
        if not documents:
            print("[process_documents]: no new documents to load")
            return
        print(
            f"[process_documents]: loaded {len(documents)} new documents from {user_folder}"
        )

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=100,
            separators=["\n\n\n", "\n\n", "\n \n", "\n", " ", ""],
            keep_separator=False,
            is_separator_regex=False,
        )
        ## create texts with the filename included
        if user_id not in GLOBAL_CHUNKED_TEXTS:
            GLOBAL_CHUNKED_TEXTS[user_id] = {}

        texts = []
        for doc in documents:
            source_path = doc.metadata.get("source", "")
            filename = os.path.basename(source_path)
            chunks = text_splitter.split_text(doc.page_content)
            for chunk in chunks:
                chunk_with_filename = f"Filename: {filename}\n{chunk}"
                new_doc = Document(
                    page_content=chunk_with_filename, metadata=doc.metadata.copy()
                )
                texts.append(new_doc)

        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        GLOBAL_FAISS_DBs[user_id] = FAISS.from_documents(texts, embeddings)
        print(f"[process_documents]: FAISS database updated for user {user_id}")
        user_faiss_filename = f"faiss_db_{user_id}"
        GLOBAL_FAISS_DBs[user_id].save_local(user_faiss_filename)
        print(f"[process_documents]: FAISS database saved for user {user_id}")

    except Exception as e:
        print(f"Error during processing documents in {user_folder}. Reason: {str(e)}")
        shutil.rmtree(user_folder)
        raise


#############################################################################################################
