from langchain_chroma import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from src.loader import load_json_files

embeddings = OllamaEmbeddings(model="nomic-embed-text")

def initialize_brain(data_path, persist_directory):
    documents = load_json_files(data_path)
    if not documents:
        print("Warning: No JSON data found to index.")
        return None
        
    vector_db = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=persist_directory
    )
    return vector_db

def get_retriever(persist_directory):
    vector_db = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )
    return vector_db.as_retriever(search_kwargs={'k': 10})