![DR_AIJSONA Logo](assets/dr_aijsona.png)

![Version](https://img.shields.io/badge/version-v2.0.0-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)
![Ollama](https://img.shields.io/badge/Ollama-Local-white?style=flat&logo=ollama)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker)
![Nginx](https://img.shields.io/badge/Nginx-Proxy-009639?style=flat&logo=nginx)

# DR_AIJSONA - Enterprise JSON Analytics Engine

A high-performance, security-first RAG (Retrieval-Augmented Generation) engine designed to analyze complex JSON datasets while enforcing strict data access policies. Optimized for ERP integrations and VPS deployment.

---

## 🔐 Advanced Security Features (v2.2.0)

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
├── src/
│   ├── main.py           # API + security middleware
│   ├── brain.py          # Multi-role RAG logic
│   ├── loader.py         # Policy-aware loader
│   └── __init__.py
├── Dockerfile
└── docker-compose.yml
```

---

## 🚀 Deployment Guide

### 1. Environment Configuration

Update your environment:

```env
JWT_SECRET=your_erp_jwt_signing_key
OLLAMA_BASE_URL=http://10.73.7.198:11434
```

---

### 2. Multi-Role Indexing

```bash
curl -X POST http://localhost:8000/retrain
```

- Reads `policy.json`
- Builds isolated FAISS indexes per role

---

## 📡 API Endpoints

### 🔹 Secure Ask AI

**Endpoint:** `/ask`  
**Method:** POST  

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Request:**

```json
{
  "question": "What is the total revenue for this quarter?"
}
```

👉 Response is filtered based on role permissions.

---

### 🔹 Role Re-indexing

**Endpoint:** `/retrain`  
**Method:** POST  

- Rebuilds all role-based indexes
- Required after data/policy updates

---

## 🐳 Volume Mapping & Persistence

| Host Path         | Container Path       | Purpose |
|------------------|---------------------|--------|
| ./data           | /app/data           | Raw datasets |
| ./policy.json    | /app/policy.json    | Access rules |
| ./faiss_indexes  | /app/faiss_indexes  | Secure vector DB |
| ./cache_data     | /app/cache_data     | Performance cache |

---

## 🧠 Performance Metrics

| Scenario            | Logic                | Response Time |
|--------------------|---------------------|--------------|
| Cached Answer      | Exact match         | < 10ms       |
| Semantic Match     | Vector similarity   | < 150ms      |
| Full RAG Cycle     | PBAC + LLM          | 1.5s – 3s    |

---

## 🛡️ Security Model

- **Zero Cloud Leakage**: Fully local inference via Ollama
- **Memory Isolation**: Role-based FAISS separation
- **Strict Access Control**: Policy-driven data visibility

---

## ⚙️ ERP Integration Highlights

- Uses existing ERP JWT authentication
- Maps roles directly to AI access layers
- Enables secure “Ask Your Data” feature

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