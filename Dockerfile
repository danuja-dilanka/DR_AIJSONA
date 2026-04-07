FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "from flashrank import Ranker; Ranker(model_name='ms-marco-MiniLM-L-12-v2')"

COPY . .

RUN mkdir -p data faiss_index cache_data semantic_cache_data && \
    chmod -R 777 data faiss_index cache_data semantic_cache_data

CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "src.api:app", "--bind", "0.0.0.0:8000", "--timeout", "120"]