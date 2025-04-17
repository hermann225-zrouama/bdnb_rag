# 🏡 BDNB Chat Application

The **BDNB Chat Application** is a Retrieval-Augmented Generation (RAG) system designed to provide conversational insights about building energy efficiency. It leverages:

- 🧠 **Ollama** for local LLM inference  
- 📚 **Qdrant** for vector similarity search  
- ⚡ **Redis** for response caching  

---

## 🔍 How It Works

This project uses a **RAG (Retrieval-Augmented Generation)** approach to answer natural language queries about building energy efficiency from the BDNB (Base de Données Nationale des Bâtiments).

### 🔄 Full Pipeline Overview

1. **Data Retrieval**
   - Source: Public BDNB datasets
   - Tools: Jobs in `rag/jobs/` fetch and clean the data.

2. **Feature Engineering**
   - Creates standardized text chunks from raw BDNB entries.
   - Stored locally in `rag/data/`.

3. **Embedding + Indexing**
   - Text chunks are embedded using `sentence-transformers/all-MiniLM-L6-v2`.
   - Stored in **Qdrant** for fast vector search.

4. **Querying**
   - User messages go through the API.
   - Top-k similar documents are retrieved via Qdrant.

5. **RAG Prompt Construction**
   - Retrieved context is appended to user prompt.
   - Prompt is sent to the local LLM (Ollama running `llama3.2:3b` by default).

6. **Response Generation**
   - Ollama generates a reply using the provided context.
   - Result is cached in Redis (TTL: 1 hour) to avoid recomputation.

---

## 🧩 Components

- **Jobs**: Data retrieval, feature engineering, and indexing pipelines.
- **API**: FastAPI backend exposing the `/chat` endpoint.
- **UI**: Streamlit frontend for user interaction.

> 🐳 Most services are containerized, but **Ollama runs on the host** for faster and more reliable inference.

---

## 🗂 Project Structure

.
├── Makefile                         # Automation for jobs, API, and UI
├── README.md                        # This file
├── check_ollama_prerequisites.sh   # Host Ollama setup verification
├── docker-compose.yml              # Docker Compose orchestration
├── entrypoint.sh                   # Legacy Ollama entrypoint (unused)
├── pyproject.toml                  # Python dependencies
├── rag                             # Backend logic (jobs, API)
│   ├── Dockerfile
│   ├── api.py
│   ├── data/
│   ├── helpers/
│   ├── jobs/
│   ├── routes/
│   ├── storage/
│   └── tools/
├── ui                              # Frontend (Streamlit)
│   ├── Dockerfile
│   ├── ui.py
│   └── tools/
└── uv.lock                         # Dependency lock file
```

---

## 💻 Prerequisites

### 🖥 Host Machine

- **OS**: Linux, macOS, or Windows (with Docker Desktop)
- **CPU**: ≥ 4 cores
- **RAM**: ≥ 4GB (6GB+ for `llama3.2:3b`)
- **Disk**: ≥ 6GB free

### 📦 Software

- Docker + Docker Compose
- Python 3.10+
- [Ollama](https://ollama.com) installed on the host

---

## ⚙️ Ollama Setup

Install and run Ollama on the host:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull llama3.2:3b  # Or use llama3.2:1b for lighter model
curl http://localhost:11434/api/tags
```

To validate your setup, run:

```bash
chmod +x check_ollama_prerequisites.sh
./check_ollama_prerequisites.sh
```

---

## 🚀 Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd bdnb-chat
```

### 2. Install Python Dependencies

```bash
pip install uv
uv sync
```

### 3. Verify Ollama Setup

```bash
./check_ollama_prerequisites.sh
```

---

## 🐳 Docker Compose Configuration

Edit `docker-compose.yml` if needed.

> Default Ollama URL: `http://host.docker.internal:11434`

If you're on **Linux** and `host.docker.internal` doesn't resolve:

```yaml
environment:
  - OLLAMA_BASE_URL=http://<your-host-ip>:11434
```

Get your host IP:

```bash
ip addr show | grep inet
```

---

## 🔧 Build & Start Services

```bash
docker-compose build
docker-compose up -d
```

This will:

- Run all jobs (retriever, feature eng, indexer)
- Start API at [http://localhost:8000](http://localhost:8000)
- Launch Streamlit UI at [http://localhost:8501](http://localhost:8501)

---

## ✅ Verify It's Working

### Test the API:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the energy efficiency of buildings in Paris?"}'
```

### Launch UI:

Open [http://localhost:8501](http://localhost:8501)

---

## ⚙️ Configuration Reference

Config is located in `rag/tools/config.py` and overridden in `docker-compose.yml`.

| Variable           | Description                         | Default                                  |
|--------------------|-------------------------------------|------------------------------------------|
| `OLLAMA_BASE_URL`  | Host Ollama server                  | `http://host.docker.internal:11434`      |
| `LLM_MODEL`        | Model name                          | `llama3.2:3b`                             |
| `EMBEDDING_MODEL`  | Embedding model                     | `sentence-transformers/all-MiniLM-L6-v2` |
| `QDRANT_HOST`      | Qdrant server host                  | `qdrant`                                  |
| `QDRANT_PORT`      | Qdrant server port                  | `6333`                                    |
| `REDIS_HOST`       | Redis server host                   | `redis`                                   |
| `REDIS_PORT`       | Redis server port                   | `6379`                                    |
| `DATA_DIR`         | Raw data directory                  | `rag/data`                                |
| `STORAGE_DIR`      | Vector index storage                | `rag/storage`                             |
| `FETCH_LIMIT`      | Limit for data pull                 | `10000`                                   |
| `REDIS_TTL`        | Cache TTL in seconds                | `3600`                                    |
| `SIMILARITY_TOP_K` | Top K results from vector search    | `5`                                       |

---

## 🧪 Usage Examples

### Start Ollama on Host

```bash
ollama serve &
```

### Verify Prereqs

```bash
./check_ollama_prerequisites.sh
```

### Launch Services

```bash
docker-compose up -d
```

---

## 🛠 Makefile Shortcuts

```bash
make run-retriever
make run-feature-eng
make run-indexer
make run-api
make run-ui
```

---

## 🔄 Switching Models

Use a lighter model for faster inference:

```bash
ollama pull llama3.2:1b
```

Update in `docker-compose.yml`:

```yaml
environment:
  - LLM_MODEL=llama3.2:1b
```

Restart services:

```bash
docker-compose up -d
```

---

## 🧯 Troubleshooting

### 🔌 Ollama Not Reachable?

```bash
curl http://localhost:11434/api/tags
ollama serve &
```

Use host IP if needed:

```yaml
environment:
  - OLLAMA_BASE_URL=http://<host-ip>:11434
```

---

### ❗ Model Not Found?

```bash
ollama list
ollama pull llama3.2:3b
```

---

### ⚠️ API 500 Errors?

```bash
docker-compose logs api
```

Test directly:

```bash
curl -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.2:3b", "messages": [{"role": "user", "content": "Hello"}]}'
```

---

### 🐌 Slow Inference?

- Use `llama3.2:1b`
- Enable GPU:

```bash
export OLLAMA_CUDA_ENABLED=1
ollama serve
```

---

## 🧰 Debugging Tools

```bash
docker stats
free -m
df -h
docker-compose logs <service>
```

Test network:

```bash
curl https://registry.ollama.ai/v2/library/llama3.2/manifests/3b
```

---

## 🤝 Contributing

- Follow [PEP8](https://peps.python.org/pep-0008/)
- Include tests
- Update `pyproject.toml` if you add dependencies

---

## 📄 License

Licensed under the **MIT License**. See [LICENSE](LICENSE) file for details.
```