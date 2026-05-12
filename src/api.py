import os
import re
import asyncio
from contextlib import asynccontextmanager

import jwt
from diskcache import Cache
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from flashrank import RerankRequest, Ranker
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from pydantic import BaseModel
from dotenv import load_dotenv

from src.brain import get_retriever, train_all_roles

# ---------------------------------------------------------------------------
# Configuration — fail fast on missing secrets
# ---------------------------------------------------------------------------

load_dotenv()

TITLE             = os.environ.get("TITLE", "DR_AIJSONA - Enterprise Edition")
OLLAMA_BASE_URL   = os.environ["OLLAMA_BASE_URL"]
OLLAMAMODEL       = os.environ["OLLAMAMODEL"]
OLLAMAEMBEDMODEL  = os.environ["OLLAMAEMBEDMODEL"]
RANKERMODEL       = os.environ.get("RANKERMODEL", "ms-marco-MiniLM-L-12-v2")
CACHE_PATH        = os.environ.get("CACHE_PATH", "./cache_data")
SEMANTIC_CACHE_PATH = os.environ.get("SEMANTIC_CACHE_PATH", "./semantic_cache_data")

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET env var must be set before starting the server.")

# ---------------------------------------------------------------------------
# App state (populated in lifespan)
# ---------------------------------------------------------------------------

class AppState:
    ranker: Ranker | None = None
    llm: ChatOllama | None = None
    embed: OllamaEmbeddings | None = None
    semantic_db: FAISS | None = None

state = AppState()
exact_cache = Cache(CACHE_PATH)

# ---------------------------------------------------------------------------
# Lifespan — replaces deprecated @app.on_event
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):
    state.embed   = OllamaEmbeddings(model=OLLAMAEMBEDMODEL, base_url=OLLAMA_BASE_URL)
    state.ranker  = Ranker(model_name=RANKERMODEL)
    state.llm     = ChatOllama(model=OLLAMAMODEL, base_url=OLLAMA_BASE_URL, temperature=0)

    # Load semantic cache DB if it already exists on disk
    sem_index = os.path.join(SEMANTIC_CACHE_PATH, "index.faiss")
    if os.path.exists(sem_index):
        try:
            state.semantic_db = await asyncio.to_thread(
                FAISS.load_local,
                SEMANTIC_CACHE_PATH,
                state.embed,
                allow_dangerous_deserialization=True,
            )
        except Exception as exc:
            print(f"[warn] Could not load semantic cache: {exc}")

    yield

    exact_cache.close()

app = FastAPI(title=TITLE, lifespan=lifespan)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

def get_user_role(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    role = payload.get("role")
    if not role:
        raise HTTPException(status_code=401, detail="Token missing 'role' claim")
    return role

def require_admin(role: str = Depends(get_user_role)) -> str:
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return role

# ---------------------------------------------------------------------------
# Semantic cache helpers
# ---------------------------------------------------------------------------

SEMANTIC_THRESHOLD = 0.98

def _is_specific_query(question: str) -> bool:
    """Returns True if question contains IDs, numbers, or specific values."""
    return bool(re.search(r'[A-Z]{2,}\d+|\d+', question))

async def check_semantic_cache(question: str) -> str | None:
    if state.semantic_db is None:
        return None
    if _is_specific_query(question):
        return None
    try:
        results = await asyncio.to_thread(
            state.semantic_db.similarity_search_with_relevance_scores,
            question,
            k=1,
        )
        if results and results[0][1] >= SEMANTIC_THRESHOLD:
            return results[0][0].page_content
    except Exception as exc:
        print(f"[warn] Semantic cache lookup failed: {exc}")
    return None


async def update_semantic_cache(question: str, answer: str) -> None:
    """Upsert answer into the semantic vector cache and persist to disk."""
    if state.embed is None:
        return
    os.makedirs(SEMANTIC_CACHE_PATH, exist_ok=True)
    try:
        if state.semantic_db is None:
            from langchain_core.documents import Document
            state.semantic_db = await asyncio.to_thread(
                FAISS.from_documents,
                [Document(page_content=answer, metadata={"question": question})],
                state.embed,
            )
        else:
            await asyncio.to_thread(
                state.semantic_db.add_texts,
                [answer],
                metadatas=[{"question": question}],
            )
        await asyncio.to_thread(state.semantic_db.save_local, SEMANTIC_CACHE_PATH)
    except Exception as exc:
        print(f"[warn] Semantic cache update failed: {exc}")

# ---------------------------------------------------------------------------
# Core RAG logic
# ---------------------------------------------------------------------------

RAG_PROMPT = ChatPromptTemplate.from_template(
    """You are a professional business assistant. Answer directly using only the context below.
Rules: never mention JSON, databases, or "provided data". Keep responses conversational and concise.

Context:
{context}

Question: {question}
Answer:"""
)

async def run_rag_chain(question: str, role: str) -> str:
    if state.llm is None or state.ranker is None:
        raise HTTPException(status_code=503, detail="AI engine not ready.")

    retriever = await asyncio.to_thread(get_retriever, role)
    if retriever is None:
        return "I don't have access to information for your role."

    docs = await asyncio.to_thread(retriever.invoke, question)
    
    if not docs:
        return "I couldn't find any relevant details in the available records."

    # Re-rank and take top-3
    passages = [{"id": i, "text": d.page_content} for i, d in enumerate(docs)]
    rerank_results = await asyncio.to_thread(
        state.ranker.rerank,
        RerankRequest(query=question, passages=passages),
    )
    context_text = "\n\n".join(r["text"] for r in rerank_results[:3])

    chain = RAG_PROMPT | state.llm | StrOutputParser()
    return await chain.ainvoke({"context": context_text, "question": question})

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

EXACT_CACHE_TTL = 1200  # seconds

@app.post("/ask")
async def ask_ai(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    role: str = Depends(get_user_role),
):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question must not be empty.")

    cache_key = f"{role}:{question.lower()}"

    # 1 — Exact cache
    cached = exact_cache.get(cache_key)
    if cached:
        return {"answer": cached, "source": "exact_cache"}

    # 2 — Semantic cache
    semantic_hit = await check_semantic_cache(question)
    if semantic_hit:
        return {"answer": semantic_hit, "source": "semantic_cache"}

    # 3 — AI generation
    try:
        answer = await run_rag_chain(question, role)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Engine error: {exc}") from exc

    # Populate both caches in the background
    background_tasks.add_task(exact_cache.set, cache_key, answer, EXACT_CACHE_TTL)
    background_tasks.add_task(update_semantic_cache, question, answer)

    return {"answer": answer, "source": "ai_engine"}


@app.post("/retrain")
async def retrain(
    background_tasks: BackgroundTasks,
    _role: str = Depends(require_admin),
):
    background_tasks.add_task(train_all_roles)
    return {"status": "rebuild_started", "message": "Indexes are being rebuilt for all roles."}


@app.get("/health")
def health():
    return {
        "status": "online",
        "model": OLLAMAMODEL,
        "llm_ready": state.llm is not None,
        "semantic_cache_loaded": state.semantic_db is not None,
    }