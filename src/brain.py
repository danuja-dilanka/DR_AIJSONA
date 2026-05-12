import json
import os

from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from dotenv import load_dotenv

from src.loader import PBACLoader

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

DATA_PATH       = os.environ.get("DATA_PATH", "./data")
SCHEMA_PATH     = os.environ.get("SCHEMA_PATH", "./schemas")
POLICY_FILE     = os.environ.get("POLICY_FILE", "./policy.json")
FAISS_BASE_PATH = os.environ.get("FAISS_BASE_PATH", "./faiss_indexes")
OLLAMA_BASE_URL = os.environ["OLLAMA_BASE_URL"]
OLLAMAEMBEDMODEL = os.environ.get("OLLAMAEMBEDMODEL", "nomic-embed-text")

embeddings = OllamaEmbeddings(model=OLLAMAEMBEDMODEL, base_url=OLLAMA_BASE_URL)
loader     = PBACLoader(DATA_PATH, SCHEMA_PATH, POLICY_FILE)

# ---------------------------------------------------------------------------
# Path helpers — directory creation is explicit, not a side effect of lookup
# ---------------------------------------------------------------------------

def _role_index_dir(role: str) -> str:
    """Return the FAISS directory path for a role. Does NOT create it."""
    return os.path.join(FAISS_BASE_PATH, role)


def _role_index_exists(role: str) -> bool:
    return os.path.exists(os.path.join(_role_index_dir(role), "index.faiss"))

# ---------------------------------------------------------------------------
# Index build helpers
# ---------------------------------------------------------------------------

def _build_index(role: str) -> FAISS | None:
    """Build and persist a FAISS index for *role*. Returns the db or None."""
    documents = loader.load_documents(role)
    if not documents:
        print(f"[brain] No documents for role '{role}'. Skipping index build.")
        return None

    vector_db = FAISS.from_documents(documents, embeddings)
    index_dir = _role_index_dir(role)
    os.makedirs(index_dir, exist_ok=True)
    vector_db.save_local(index_dir)
    print(f"[brain] Index built for role '{role}' ({len(documents)} docs).")
    return vector_db


def _load_index(role: str) -> FAISS | None:
    """Load a persisted FAISS index from disk. Returns None on failure."""
    index_dir = _role_index_dir(role)
    try:
        return FAISS.load_local(
            index_dir,
            embeddings,
            allow_dangerous_deserialization=True,
        )
    except Exception as exc:
        print(f"[brain] Failed to load index for role '{role}': {exc}")
        return None

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_retriever(role: str):
    """
    Return a retriever for *role*, building the index on first access.

    Returns None if no documents are available for the role.
    """
    vector_db = _load_index(role) if _role_index_exists(role) else None

    if vector_db is None:
        print(f"[brain] Cache miss for role '{role}'. Building index now...")
        vector_db = _build_index(role)

    if vector_db is None:
        return None

    return vector_db.as_retriever(search_kwargs={"k": 10})


def train_all_roles() -> None:
    """Rebuild FAISS indexes for every role defined in the policy file."""
    if not os.path.exists(POLICY_FILE):
        print(f"[brain] Policy file not found: {POLICY_FILE}")
        return

    with open(POLICY_FILE, "r") as f:
        policies = json.load(f).get("policies", {})

    # Collect all roles mentioned in policy values, always include "public"
    all_roles: set[str] = {"public"}
    for roles_list in policies.values():
        all_roles.update(roles_list)

    print(f"[brain] Starting retrain for roles: {sorted(all_roles)}")

    for role in sorted(all_roles):
        _build_index(role)

    print("[brain] Retrain complete.")