import os
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks, Header, Depends
from pydantic import BaseModel
from diskcache import Cache
import jwt

# LangChain & AI Imports
from langchain_ollama import OllamaEmbeddings, ChatOllama
# from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Performance & Custom Imports
from flashrank import Ranker, RerankRequest
from src.brain import get_retriever, train_all_roles

app = FastAPI(title=os.getenv("TITLE", "DR_AIJSONA - Enterprise Edition"))

# Environment Variables
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMAMODEL = os.getenv("OLLAMAMODEL", "qwen2.5-coder:1.5b")
OLLAMAEMBEDMODEL = os.getenv("OLLAMAEMBEDMODEL", "nomic-embed-text")
RANKERMODEL = os.getenv("RANKERMODEL", "ms-marco-MiniLM-L-12-v2")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")

# Cache Paths
CACHE_PATH = os.getenv("OLLAMA_BASE_URL", "./cache_data")
SEMANTIC_CACHE_PATH = os.getenv("OLLAMA_BASE_URL", "./semantic_cache_data")

# Global Objects
ranker_client = None
llm = None
exact_cache = Cache(CACHE_PATH)

cache_embeddings = None
semantic_cache_db = None

class QueryRequest(BaseModel):
    question: str

@app.on_event("startup")
async def startup_event():
    global ranker_client, llm, cache_embeddings, semantic_cache_db
    
    cache_embeddings = OllamaEmbeddings(model=OLLAMAEMBEDMODEL, base_url=OLLAMA_BASE_URL)
    ranker_client = Ranker(model_name=RANKERMODEL)
    llm = ChatOllama(model=OLLAMAMODEL, base_url=OLLAMA_BASE_URL, temperature=0)

# --- Security Dependency ---
def get_user_role(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("role", "public")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Session")

# --- Core RAG Logic ---
async def run_rag_chain(question: str, role: str):
    global llm
    
    if llm is None:
        raise HTTPException(status_code=500, detail="AI Engine not initialized. Please try again.")
    
    # 1. Get the Role-Specific Retriever
    retriever = get_retriever(role)
    if not retriever:
        return "I'm sorry, I don't have access to information for your role."

    # 2. Retrieve Documents
    docs = await asyncio.to_thread(retriever.invoke, question)
    if not docs:
        return "I couldn't find any relevant details in the available records."

    # 3. Re-rank results for higher precision
    passages = [{"id": i, "text": d.page_content} for i, d in enumerate(docs)]
    rerank_req = RerankRequest(query=question, passages=passages)
    rerank_results = ranker_client.rerank(rerank_req)
    
    context_text = "\n\n".join([d["text"] for d in rerank_results[:3]])

    # 4. Prompt & LLM Execution
    template = """You are a professional business assistant. Use the context to answer directly.
    STRICT RULES: No mention of 'JSON', 'database', or 'provided data'. Keep it conversational.
    
    Context: {context}
    Question: {question}
    Answer:"""
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    
    return await chain.ainvoke({"context": context_text, "question": question})

# --- Cache Logic ---
def check_semantic_cache(question: str):
    try:
        results = semantic_cache_db.similarity_search_with_relevance_scores(question, k=1)
        if results and results[0][1] > 0.90: # Slightly higher threshold for safety
            return results[0][0].page_content
    except: pass
    return None

# --- Endpoints ---
@app.post("/ask")
async def ask_ai(request: QueryRequest, background_tasks: BackgroundTasks, role: str = Depends(get_user_role)):
    query = request.question.strip()
    cache_key = f"{role}:{query.lower()}" # Role-based cache key for security

    # 1. Exact Cache
    cached_val = exact_cache.get(cache_key)
    if cached_val:
        return {"answer": cached_val, "source": "cache"}

    # 2. Semantic Cache
    semantic_val = await asyncio.to_thread(check_semantic_cache, query)
    if semantic_val:
        return {"answer": semantic_val, "source": "semantic_cache"}

    # 3. AI Generation
    try:
        response = await run_rag_chain(query, role)
        
        # Update caches in background
        background_tasks.add_task(exact_cache.set, cache_key, response, expire=1200) 
        
        return {"answer": response, "source": "ai_engine"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Engine Error: {str(e)}")

@app.post("/retrain")
async def retrain(background_tasks: BackgroundTasks):
    background_tasks.add_task(train_all_roles)
    return {"status": "rebuild_started", "message": "Indices are being updated for all roles."}

@app.get("/health")
def health():
    return {"status": "online", "model": OLLAMAMODEL}