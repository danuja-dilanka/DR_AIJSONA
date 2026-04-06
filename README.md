![DR_AIJSONA Logo](assets/dr_aijsona.png)

![Version](https://img.shields.io/badge/version-v1.0.0-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)
![Python 3.9+](https://img.shields.io/badge/python-3.9+-3776AB?style=flat&logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Privacy](https://img.shields.io/badge/Data%20Privacy-High-green)

# AI-Powered JSON Analytics Engine (High Performance)

A FastAPI-based AI system designed to intelligently identify relationships (links) between multiple JSON files and provide answers in natural language. Built with Semantic Caching, Asynchronous Processing, and Local LLMs to ensure high speed, scalability, and full data privacy.

---

## ✨ Key Features

- **Multi-File Linking**: Automatically detects relationships across JSON files (e.g., `customer_id` → customers.json).
- **Dual-Layer Caching**:
  - **Exact Match Cache**: Instant responses using DiskCache.
  - **Semantic Cache**: Vector similarity-based reuse of previous answers.
- **High Performance**: Async processing with FastAPI + background tasks.
- **Privacy-First**: Runs fully local using Ollama (no external API calls).
- **Production Ready**: Optimized for Docker + Nginx deployment.

---

## 🛠️ Project Structure

```
my-ai-analyzer/
├── data/                # Raw JSON data files
├── src/
│   ├── loader.py        # JSON processing
│   ├── brain.py         # Vector DB + retrieval
│   └── api.py           # FastAPI app + caching
├── brain_data/          # Persistent vector storage
├── cache_data/          # Exact match cache
├── semantic_cache_data/ # Semantic cache storage
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## ⚙️ Installation & Setup

### 1. Prerequisites

- Python 3.10+
- Ollama installed and running

### Required Models

```bash
ollama pull qwen2.5-coder:1.5b
ollama pull nomic-embed-text
```

---

### 2. Manual Setup

```bash
pip install -r requirements.txt
```

Place your JSON files inside:

```
data/
```

Start the API:

```bash
python -m src.api
```

---

## 📡 API Documentation

### 🔹 Ask AI

**Endpoint:** `/ask`  
**Method:** `POST`

#### Request

```json
{
  "question": "What is the total price of products bought by Amara?"
}
```

#### Response

```json
{
  "status": "success",
  "answer": "Amara bought a Mouse for 2,500 LKR.",
  "source": "ai_engine"
}
```

---

### 🔹 Health Check

**Endpoint:** `/health`  
**Method:** `GET`

---

## 🐳 Docker Deployment

```bash
docker-compose up -d --build
```

- Runs in detached mode
- Auto-restart enabled
- Ideal for VPS deployment

---

## 🛡️ Performance Tuning

- **Cache Expiry**: 1200 seconds (20 minutes)
- **Semantic Similarity Threshold**: 0.88
- **Async Background Tasks**: Cache writes happen after response

---

## ⚡ Architecture Overview

```
User Query
   ↓
Exact Cache (DiskCache)
   ↓ (miss)
Semantic Cache (Vector Similarity)
   ↓ (miss)
Vector DB Retrieval (brain.py)
   ↓
LLM (Ollama - Local)
   ↓
Response + Async Cache Store
```

---

## 🧠 Example Use Cases

- ERP Data Analysis (Sales, Customers, Inventory)
- Financial Insights from JSON exports
- Log analysis & anomaly detection
- AI-powered dashboards

---

## 🔐 Security & Privacy

- Fully local inference (Ollama)
- No external API calls
- Suitable for sensitive business data

---

## 📄 License

This project is licensed under the MIT License.

---

## 🤝 Contributing

Contributions and feature requests are welcome!

---

## 👨‍💻 Maintainer

Developed by **Danuja Dilanka**
