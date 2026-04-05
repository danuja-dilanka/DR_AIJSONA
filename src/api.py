import os
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from diskcache import Cache
from langchain_community.llms import Ollama
from langchain_chroma import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from src.brain import initialize_brain, get_retriever

app = FastAPI(title="AI JSON Analyzer API")

DATA_PATH = "./data"
BRAIN_PATH = "./brain_data"
SEMANTIC_CACHE_PATH = "./semantic_cache_data"

chain = None
exact_cache = Cache('./cache_data')
cache_embeddings = OllamaEmbeddings(model="nomic-embed-text")
semantic_cache_db = Chroma(persist_directory=SEMANTIC_CACHE_PATH, embedding_function=cache_embeddings)

class QueryRequest(BaseModel):
    question: str

@app.on_event("startup")
async def startup_event():
    global chain
    if not os.path.exists(BRAIN_PATH) or not os.listdir(BRAIN_PATH):
        initialize_brain(DATA_PATH, BRAIN_PATH)
    
    retriever = get_retriever(BRAIN_PATH)
    llm = Ollama(model="qwen2.5-coder:1.5b")
    
    template = """You are a professional business assistant. 
    Use the following pieces of information to answer the user's question directly. 
    STRICT RULES:
    1. Do NOT mention 'JSON', 'files', 'context', or 'database'.
    2. Do NOT say 'Based on the provided data'.
    3. Just provide the final answer naturally.
    Context: {context}
    Question: {question}
    Answer:"""
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = ({"context": retriever, "question": RunnablePassthrough()} | prompt | llm | StrOutputParser())

def get_semantic_cache(question: str):
    try:
        results = semantic_cache_db.similarity_search_with_relevance_scores(question, k=1)
        if results and results[0][1] > 0.88: # 88% similarity threshold
            return results[0][0].page_content
    except:
        pass
    return None

def update_caches(question: str, answer: str):
    exact_cache.set(question.lower(), answer, expire=1200)
    semantic_cache_db.add_texts(texts=[answer], metadatas=[{"question": question}])

@app.post("/ask")
async def ask_ai(request: QueryRequest, background_tasks: BackgroundTasks):
    query = request.question.strip()
    
    cached_val = exact_cache.get(query.lower())
    if cached_val:
        return {"status": "success", "answer": cached_val, "source": "exact_cache"}

    loop = asyncio.get_event_loop()
    semantic_val = await loop.run_in_executor(None, get_semantic_cache, query)
    if semantic_val:
        return {"status": "success", "answer": semantic_val, "source": "semantic_cache"}

    try:
        response = await chain.ainvoke(query)
        
        background_tasks.add_task(update_caches, query, response)
        
        return {"status": "success", "answer": response, "source": "ai_engine"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "healthy"}