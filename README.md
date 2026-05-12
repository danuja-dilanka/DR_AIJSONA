![DR_AIJSONA Logo](assets/dr_aijsona.png)

![Version](https://img.shields.io/badge/version-v2.3.0-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)
![Ollama](https://img.shields.io/badge/Ollama-Local-white?style=flat&logo=ollama)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker)
![Nginx](https://img.shields.io/badge/Nginx-Proxy-009639?style=flat&logo=nginx)

# DR_AIJSONA - Enterprise JSON Analytics Engine

A high-performance, security-first RAG (Retrieval-Augmented Generation) engine designed to analyze complex JSON datasets while enforcing strict data access policies. Optimized for ERP integrations and VPS deployment.

---

## 🔐 Advanced Security Features

- **PBAC (Policy-Based Access Control)**  
  Restricts AI knowledge based on user roles (Admin, Manager, Staff, etc.)

- **JWT Authentication**  
  Integrates with external ERP tokens for role-based identity

- **Role-Isolated Vector DBs**  
  Separate FAISS indexes per role to prevent data leakage

- **Dynamic Chain Construction**  
  AI pipeline adapts dynamically based on user permissions

---

## 🛠️ Microservices Architecture

```
User Query + JWT
        ↓
   [Nginx Proxy]
        ↓
[FastAPI Engine (PBAC Layer)]
        ↓
 Check Role Index
        ↓
 [Role-Specific FAISS]
        ↓
 [Re-Ranker (Flashrank)]
        ↓
 [Ollama Local LLM]
```

---

## 📂 Project Structure

```
DR_AIJSONA/
├── data/                 # Raw JSON files
├── schemas/              # JSON schema definitions
├── policy.json           # PBAC rules
├── faiss_indexes/        # Role-based vector DBs
├── cache_data/           # Exact match query cache
├── semantic_cache_data/  # Semantic similarity cache
├── src/
│   ├── api.py            # API + security middleware
│   ├── brain.py          # Multi-role RAG logic
│   ├── loader.py         # Policy-aware loader with relation resolver
│   └── __init__.py
├── .env
├── Dockerfile
└── docker-compose.yml
```

---

## ✨ What's New in v2.3.0

### 🔗 Cross-Schema Relation Resolution
The loader now supports a `relations` block in schemas. Related records from other JSON files are automatically looked up, filtered by role policy, and merged inline into each document at index time — giving the LLM full denormalized context per chunk.

**Before (v2.0):**
```
invoice_number: INV001 | quantity: 2 | total: 500
```
**After (v2.3):**
```
invoice_number: INV001 | quantity: 2 | total: 500 | customer_id__name: Kasun | customer_id__city: Colombo | product_id__name: Laptop
```

This enables cross-table questions like:
- *"What did Kasun buy?"*
- *"Which invoices are for Laptops?"*
- *"Total sales for Colombo customers?"*

### 🧠 Smarter Semantic Cache
Queries containing specific IDs, invoice numbers, or numeric values are now excluded from semantic cache and always routed to the full RAG pipeline — preventing incorrect cached answers for queries that differ only by a specific value (e.g. `INV001` vs `INV002`).

### 🔄 Cache Auto-Invalidation on Retrain
The `/retrain` endpoint now automatically clears both the exact cache and semantic cache before rebuilding indexes, eliminating stale answers after data or schema updates.

### 📁 Schema File Caching
Data and schema files are cached in memory during a `load_documents` call, so relation resolution does not re-read the same file multiple times during indexing.

### 🔁 Recursive Relation Resolution
Relations are resolved recursively — e.g. `invoices → products → category` — with a circular reference guard to prevent infinite loops.

---

## 📋 Schema Format

### Basic Schema
```json
{
  "schema_name": "Customers Records",
  "attributes": {
    "customer_id": { "type": "string", "policy": "customer_details", "visibility": true },
    "name":        { "type": "string", "policy": "customer_details", "visibility": true },
    "city":        { "type": "string", "policy": "customer_details", "visibility": true }
  }
}
```

### Schema with Relations
```json
{
  "schema_name": "Invoices Records",
  "relations": {
    "customer_id": { "references": "customers.json", "foreign_key": "customer_id" },
    "product_id":  { "references": "products.json",  "foreign_key": "product_id"  }
  },
  "attributes": {
    "invoice_id":     { "type": "string", "policy": "sales_access", "visibility": false },
    "customer_id":    { "type": "string", "policy": "sales_access", "visibility": false },
    "product_id":     { "type": "string", "policy": "sales_access", "visibility": false },
    "invoice_number": { "type": "string", "policy": "sales_access", "visibility": true  },
    "quantity":       { "type": "float",  "policy": "sales_access", "visibility": true  },
    "total":          { "type": "float",  "policy": "sales_access", "visibility": true  }
  }
}
```

### Attribute Configuration

| Field        | Type    | Description |
|--------------|---------|-------------|
| `type`       | string  | Data type (`string`, `float`, `int`, etc.) |
| `policy`     | string  | Policy name required to access this field. Omit for universal access. |
| `visibility` | boolean | `true` = included in RAG context. `false` = stored in metadata only. |

### Relation Configuration

| Field        | Description |
|--------------|-------------|
| `references` | Filename of the related data file (e.g. `customers.json`) |
| `foreign_key`| Field name in the referenced file to match against |

> **Note:** Only fields the current role is permitted to see (per the related schema's policies) are merged in. Relation resolution is recursive and circular-reference safe.

---

## 🚀 Deployment Guide

### 1. Environment Configuration

Create a `.env` file in the project root:

```env
TITLE=DR_AIJSONA - Enterprise Edition
OLLAMA_BASE_URL=http://localhost:11434
OLLAMAMODEL=llama3
OLLAMAEMBEDMODEL=nomic-embed-text
JWT_SECRET=your_erp_jwt_signing_key
RANKERMODEL=ms-marco-MiniLM-L-12-v2
DATA_PATH=./data
SCHEMA_PATH=./schemas
POLICY_FILE=./policy.json
FAISS_BASE_PATH=./faiss_indexes
CACHE_PATH=./cache_data
SEMANTIC_CACHE_PATH=./semantic_cache_data
```

### 2. Policy Configuration

Define roles and their permitted policies in `policy.json`:

```json
{
  "policies": {
    "customer_details": ["admin", "manager", "sales"],
    "sales_access":     ["admin", "manager", "sales"],
    "hr_access":        ["admin", "hr"]
  }
}
```

### 3. Build Indexes

```bash
curl -X POST http://localhost:8000/retrain \
  -H "Authorization: Bearer <ADMIN_JWT_TOKEN>"
```

- Clears existing caches
- Reads `policy.json`
- Resolves relations and builds isolated FAISS indexes per role

---

## 📡 API Endpoints

### 🔹 Ask AI

**`POST /ask`**

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Request:**
```json
{
  "question": "Which city is the customer on invoice INV002?"
}
```

**Response:**
```json
{
  "answer": "The customer on invoice INV002 is from Kandy.",
  "source": "ai_engine"
}
```

Response `source` values:

| Value            | Meaning |
|------------------|---------|
| `exact_cache`    | Returned from exact match cache (< 10ms) |
| `semantic_cache` | Returned from semantic similarity cache (< 150ms) |
| `ai_engine`      | Full RAG pipeline executed (1.5s – 3s) |

> **Note:** Queries containing specific IDs or numbers (e.g. `INV002`, `C001`) always bypass semantic cache and run the full RAG pipeline.

---

### 🔹 Retrain Indexes

**`POST /retrain`** *(Admin only)*

Clears all caches and rebuilds all role-based FAISS indexes.

```bash
curl -X POST http://localhost:8000/retrain \
  -H "Authorization: Bearer <ADMIN_JWT_TOKEN>"
```

**Response:**
```json
{
  "status": "rebuild_started",
  "message": "Indexes are being rebuilt for all roles."
}
```

---

### 🔹 Health Check

**`GET /health`**

```json
{
  "status": "online",
  "model": "llama3",
  "llm_ready": true,
  "semantic_cache_loaded": true
}
```

---

## 🐳 Volume Mapping & Persistence

| Host Path              | Container Path              | Purpose              |
|------------------------|-----------------------------|----------------------|
| `./data`               | `/app/data`                 | Raw JSON datasets    |
| `./schemas`            | `/app/schemas`              | Schema definitions   |
| `./policy.json`        | `/app/policy.json`          | Access rules         |
| `./faiss_indexes`      | `/app/faiss_indexes`        | Role vector indexes  |
| `./cache_data`         | `/app/cache_data`           | Exact match cache    |
| `./semantic_cache_data`| `/app/semantic_cache_data`  | Semantic cache       |

---

## 🧠 Performance Metrics

| Scenario          | Logic               | Response Time |
|-------------------|---------------------|---------------|
| Exact cache hit   | Exact match         | < 10ms        |
| Semantic cache hit| Vector similarity   | < 150ms       |
| Full RAG cycle    | PBAC + LLM          | 1.5s – 3s     |

---

## 🛡️ Security Model

- **Zero Cloud Leakage** — Fully local inference via Ollama
- **Memory Isolation** — Role-based FAISS separation
- **Strict Access Control** — Policy-driven field-level visibility
- **ID-Aware Caching** — Specific value queries always bypass semantic cache

---

## ⚙️ ERP Integration Highlights

- Uses existing ERP JWT authentication
- Maps roles directly to AI access layers
- Enables secure "Ask Your Data" feature across any JSON dataset
- Cross-table relation resolution works with any schema shape

---

## 📄 License

MIT License

---

## 🤝 Contributing

Contributions and improvements are welcome!

---

## 👨‍💻 Maintainer

**Danuja Dilanka**  
Optimized for Enterprise ERP Systems  
[https://www.linkedin.com/in/danuja-dilanka/](https://www.linkedin.com/in/danuja-dilanka/)