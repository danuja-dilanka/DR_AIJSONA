import os
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from diskcache import Cache

# LangChain & AI Imports
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

# Performance Imports
from flashrank import Ranker, RerankRequest
from src.brain import get_retriever, retrain_brain

app = FastAPI(title="AI JSON Analyzer API - Ultra Edition")

DATA_PATH = "./data"
FAISS_PATH = "./faiss_index"
SEMANTIC_CACHE_PATH = "./semantic_cache_data"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

chain = None
ranker_client = None
base_retriever = None

exact_cache = Cache('./cache_data')
cache_embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_BASE_URL)
semantic_cache_db = Chroma(persist_directory=SEMANTIC_CACHE_PATH, embedding_function=cache_embeddings)

class QueryRequest(BaseModel):
    question: str

@app.on_event("startup")
async def startup_event():
    global chain, ranker_client, base_retriever
    
    print("⏳ Loading Re-ranker model...")
    ranker_client = Ranker(model_name="ms-marco-MiniLM-L-12-v2")
    
    base_retriever = get_retriever(FAISS_PATH, DATA_PATH)

    llm = ChatOllama(model="qwen2.5-coder:1.5b", base_url=OLLAMA_BASE_URL, temperature=0)

    template = """You are a professional business assistant. 
    Use the provided information to answer directly.
    STRICT RULES:
    1. Do NOT mention 'JSON', 'files', 'context', or 'database'.
    2. Do NOT say 'Based on the provided data'.
    3. Keep the answer natural and conversational.

    Context: {context}
    Question: {question}
    Answer:"""

    prompt = ChatPromptTemplate.from_template(template)

    def retrieve_and_rerank(question):
        docs = base_retriever.invoke(question)
        if not docs:
            return "I couldn't find any information regarding that."

        passages = [{"id": i, "text": d.page_content} for i, d in enumerate(docs)]
        
        request = RerankRequest(query=question, passages=passages)
        rerank_results = ranker_client.rerank(request)
        
        top_docs = rerank_results[:3]
        return "\n\n".join([d["text"] for d in top_docs])
    
    context_node = RunnableLambda(lambda q: retrieve_and_rerank(q))

    chain = (
        {
            "context": context_node,
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    print("🚀 API is online with Flashrank Re-ranking!")

# --- Caching Functions ---
def get_semantic_cache(question: str):
    try:
        results = semantic_cache_db.similarity_search_with_relevance_scores(question, k=1)
        if results and results[0][1] > 0.88:
            return results[0][0].page_content
    except:
        pass
    return None

def update_caches(question: str, answer: str):
    exact_cache.set(question.lower(), answer, expire=1200)
    semantic_cache_db.add_texts(texts=[answer], metadatas=[{"question": question}])

# --- Endpoints ---
@app.post("/ask")
async def ask_ai(request: QueryRequest, background_tasks: BackgroundTasks):
    query = request.question.strip()
    
    # Check Exact Cache
    cached_val = exact_cache.get(query.lower())
    if cached_val:
        return {"status": "success", "answer": cached_val, "source": "exact_cache"}

    # Check Semantic Cache
    loop = asyncio.get_event_loop()
    semantic_val = await loop.run_in_executor(None, get_semantic_cache, query)
    if semantic_val:
        return {"status": "success", "answer": semantic_val, "source": "semantic_cache"}

    try:
        # AI Processing
        response = await chain.ainvoke(query)
        
        # Background updates to keep the API fast
        background_tasks.add_task(update_caches, query, response)
        
        return {"status": "success", "answer": response, "source": "ai_engine"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/retrain")
async def retrain(background_tasks: BackgroundTasks):
    def update_task():
        global base_retriever
        new_db = retrain_brain(DATA_PATH, FAISS_PATH)
        base_retriever = new_db.as_retriever()
        
    background_tasks.add_task(update_task)
    return {"status": "Updated"}

@app.get("/health")
def health():
    return {"status": "online"}