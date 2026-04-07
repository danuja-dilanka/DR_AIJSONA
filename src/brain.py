import os
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from src.loader import load_json_files

embeddings = OllamaEmbeddings(model="nomic-embed-text")

def initialize_brain(data_path, faiss_path):
    documents = load_json_files(data_path)
    if not documents:
        return None
    vector_db = FAISS.from_documents(documents, embeddings)
    vector_db.save_local(faiss_path)
    return vector_db

def get_retriever(faiss_path, data_path):
    faiss_file = os.path.join(faiss_path, "index.faiss")
    
    if not os.path.exists(faiss_file):
        print(f"⚠️ FAISS index file not found at {faiss_file}. Initializing brain...")
        initialize_brain(data_path, faiss_path)
    
    vector_db = FAISS.load_local(
        faiss_path, 
        embeddings, 
        allow_dangerous_deserialization=True
    )
    return vector_db.as_retriever(search_kwargs={'k': 10})

def retrain_brain(data_path, faiss_path):
    documents = load_json_files(data_path)
    vector_db = FAISS.from_documents(documents, embeddings)
    vector_db.save_local(faiss_path)
    return vector_db