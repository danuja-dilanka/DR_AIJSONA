import os
import json
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from src.loader import PBACLoader

DATA_PATH = os.getenv("DATA_PATH", "./data")
SCHEMA_PATH = os.getenv("SCHEMA_PATH", "./schemas")
POLICY_FILE = os.getenv("POLICY_FILE", "./policy.json")
FAISS_BASE_PATH = os.getenv("FAISS_PATH", "./faiss_indexes")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")

embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_BASE_URL)
loader = PBACLoader(DATA_PATH, SCHEMA_PATH, POLICY_FILE)

def get_role_path(role):
    path = os.path.join(FAISS_BASE_PATH, role)
    os.makedirs(path, exist_ok=True)
    return path

def initialize_single_role(role='public'):
    
    documents = loader.load_documents(role)
    
    if not documents:
        return None

    vector_db = FAISS.from_documents(documents, embeddings)
    
    role_path = get_role_path(role)
    vector_db.save_local(role_path)
    
    return vector_db

def train_all_roles():
    
    if not os.path.exists(POLICY_FILE):
        return

    with open(POLICY_FILE, 'r') as f:
        policies = json.load(f).get("policies", {})
    
    all_roles = set()
    for roles_list in policies.values():
        all_roles.update(roles_list)

    for role in all_roles:
        documents = loader.load_documents(role)
        
        if documents:
            vector_db = FAISS.from_documents(documents, embeddings)
            role_path = get_role_path(role)
            vector_db.save_local(role_path)
        else:
            print(f"No documents accessible for {role}. Skipping.")

    print("Background training complete.")

def get_retriever(role):
    role_path = get_role_path(role)
    faiss_file = os.path.join(role_path, "index.faiss")
    vector_db = None

    if os.path.exists(faiss_file):
        try:
            vector_db = FAISS.load_local(
                role_path, 
                embeddings, 
                allow_dangerous_deserialization=True
            )
        except Exception as e:
            print(f"Error loading local FAISS for {role}: {e}")

    if vector_db is None:
        print(f"Cache miss for {role}. Training now...")
        vector_db = initialize_single_role(role)

    if vector_db is None:
        return None
    
    return vector_db.as_retriever(search_kwargs={'k': 10})