![DR_AIJSONA Logo](assets/dr_aijsona.png)

![Version](https://img.shields.io/badge/version-v1.1.0-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)
![Ollama](https://img.shields.io/badge/Ollama-Local-white?style=flat&logo=ollama)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker)
![Nginx](https://img.shields.io/badge/Nginx-Proxy-009639?style=flat&logo=nginx)

# AI-Powered JSON Analytics Engine (Production Grade)

A high-performance FastAPI-based system designed to intelligently analyze relationships across multiple JSON files using local LLMs. Optimized for **VPS deployment** with a full microservices architecture including Nginx reverse proxy and automated container networking.

---

## ✨ Key Features

- **Multi-File Linking**: Intelligent relationship detection across JSON schemas (e.g., `customer_id` linking).
- **Dual-Layer Caching**:
  - **Exact Match Cache**: Instant retrieval using DiskCache.
  - **Semantic Cache**: AI similarity-based answer reuse.
- **Production Networking**: Docker bridge networking between API and Ollama.
- **Reverse Proxy**: Nginx integration for ports 80/443.
- **Persistent Storage**: Volume mapping ensures durability across restarts.

---

## 🛠️ Microservices Architecture

```
User Query (80/443)
        ↓
   [Nginx Proxy]
        ↓
[FastAPI Engine (Gunicorn)]
        ↔
 [Dual-Layer Cache]
        ↓
   [Vector DB (FAISS)]
        ↓
 [Ollama Service]
```

---

## 📂 Project Structure

```
DR_AIJSONA/
├── data/                 # Raw JSON files (Host Mounted)
├── faiss_index/          # Vector DB storage
├── cache_data/           # Exact cache
├── semantic_cache_data/  # Semantic cache
├── nginx/
│   └── default.conf      # Reverse proxy config
├── src/
│   ├── api.py            # FastAPI app
│   ├── brain.py          # RAG + vector logic
│   └── loader.py         # JSON processing
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 🚀 Deployment Guide (VPS / Local)

### 1. Prerequisites

- Docker & Docker Compose
- Open ports: 80, 443

---

### 2. Environment Configuration

Internal service communication:

```
http://ollama:11434
```

---

### 3. One-Command Setup

```bash
docker-compose up -d --build
```

---

### 4. Initialize AI Model

```bash
docker exec -it ollama_service ollama run llama3
```

---

## 📡 API Endpoints

### 🔹 Ask AI

**Endpoint:** `/ask`  
**Method:** POST

```json
{
  "question": "Show me total sales for Amara across all datasets."
}
```

---

### 🔹 Re-index Data

**Endpoint:** `/retrain`  
**Method:** POST  

Use after adding new JSON files.

---

## 🐳 Docker Configuration (Technical Details)

### Volume Mapping

| Host Path              | Container Path        | Purpose |
|----------------------|----------------------|--------|
| ./data               | /app/data            | JSON data |
| ./faiss_index        | /app/faiss_index     | Vector DB |
| ./ollama_data        | /root/.ollama        | LLM models |

---

### Optimization

- **Gunicorn Workers**: 4 workers
- **PythonPath**: `/app`
- **Preloaded Models**: Flashrank cached during build

---

## 🧠 Performance Metrics

| Scenario            | Response Time |
|--------------------|--------------|
| Cache Hit          | < 10ms       |
| Semantic Cache Hit | < 150ms      |
| LLM Inference      | Hardware dependent (4GB+ RAM recommended) |

---

## 🔐 Security Considerations

- Fully local inference (Ollama)
- No external API calls
- Ideal for sensitive enterprise data

---

## 📄 License

This project is licensed under the MIT License.

---

## 🤝 Contributing

Contributions and improvements are welcome!

---

## 👨‍💻 Maintainer

Developed by **Danuja Dilanka**
