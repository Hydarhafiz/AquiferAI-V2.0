# Saline Aquifer CO2 Storage Chatbot

A full-stack application for analyzing CO2 storage suitability in saline aquifers using a chatbot interface powered by local LLMs (Ollama), Neo4j graph database, and PostgreSQL.

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React Client  │────▶│  FastAPI Server │────▶│     Ollama      │
│   (Vite + TS)   │     │   (Python 3.10) │     │  (LLM Models)   │
│   Port: 5173    │     │   Port: 8000    │     │  Port: 11434    │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
           ┌─────────────────┐       ┌─────────────────┐
           │   PostgreSQL    │       │     Neo4j       │
           │  (Chat History) │       │ (Knowledge Graph│
           │   Port: 5432    │       │   Port: 7687    │
           └─────────────────┘       └─────────────────┘
```

## Prerequisites

- **Docker** & **Docker Compose** (v2.0+)
- **NVIDIA GPU** with drivers installed (for Ollama)
- **NVIDIA Container Toolkit** (`nvidia-docker2`)
- **Node.js** (v18+) - for frontend development
- ~16GB RAM recommended
- ~20GB disk space (for LLM models)

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/Hydarhafiz/AquiferAI-V2.0.git
cd saline-aquifer-chatbot
```

### 2. Configure Environment

Create `server/.env` file:

```env
# PostgreSQL Configuration
DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/co2_chat_db
INIT_DB=true

# Neo4j Configuration
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password_here

# Ollama Configuration
OLLAMA_BASE_URL=http://ollama:11434
GENERATE_CYPHER_MODEL=qwen2.5-coder:7b
AI_CHATBOT_MODEL=llama3:8b
```

### 3. Start Backend Services (Docker)

```bash
cd server
docker compose up -d --build
```

This will start:
- FastAPI server on `http://localhost:8000`
- PostgreSQL on `localhost:5432`
- Neo4j on `http://localhost:7474` (browser) and `bolt://localhost:7687`
- Ollama on `http://localhost:11434`

**First run note:** Ollama will automatically download the required models (`qwen2.5-coder:7b` and `llama3:8b`). This may take 10-20 minutes depending on your internet speed.

### 4. Start Frontend

```bash
cd client
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`

### 5. Verify Everything is Running

```bash
# Check all containers are healthy
docker compose ps

# Test API
curl http://localhost:8000/docs

# Test Ollama
curl http://localhost:11434/api/tags
```

## Project Structure

```
saline-aquifer-chatbot/
├── server/                    # Backend (FastAPI)
│   ├── app/                   # Application code
│   │   ├── api/endpoints/     # API routes
│   │   ├── services/          # Business logic
│   │   ├── models/            # Database models
│   │   └── init_db.py         # Database initialization
│   ├── docker-compose.yml     # Docker services config
│   ├── Dockerfile             # FastAPI container
│   ├── Dockerfile.ollama      # Ollama container with auto-pull
│   ├── ollama-startup.sh      # Model auto-download script
│   ├── requirements.txt       # Python dependencies
│   └── main.py                # FastAPI entry point
│
├── client/                    # Frontend (React + Vite)
│   ├── src/                   # React source code
│   ├── package.json           # Node dependencies
│   └── vite.config.ts         # Vite configuration
│
└── .venv/                     # Python virtual env (local dev only)
```

## Development

### Running Backend Locally (without Docker)

```bash
cd server

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Download SpaCy model
python -m spacy download en_core_web_md

# Run (requires external PostgreSQL, Neo4j, Ollama)
uvicorn main:app --reload --port 8000
```

### Running Frontend

```bash
cd client
npm install
npm run dev      # Development
npm run build    # Production build
```

## API Documentation

Once running, access:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Docker vs Local Development

| Component | Docker | Local |
|-----------|--------|-------|
| **Backend (FastAPI)** | Recommended | Possible but needs external DBs |
| **PostgreSQL** | Recommended | Can use local/cloud instance |
| **Neo4j** | Recommended | Can use local/cloud instance |
| **Ollama** | Recommended | Install locally with GPU |
| **Frontend** | Not needed | Run with `npm run dev` |

**Recommendation:** Run databases + Ollama in Docker, frontend locally for hot-reload during development.

---

## Troubleshooting

### Ollama GPU Issues

```bash
# Check NVIDIA driver
nvidia-smi

# Check Docker can see GPU
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
```

### Neo4j Connection Refused

```bash
# Check Neo4j is healthy
docker compose logs neo4j

# Wait for full startup (can take 30-60 seconds)
docker compose ps
```

### Models Not Downloading

```bash
# Manually pull models
docker compose exec ollama ollama pull qwen2.5-coder:7b
docker compose exec ollama ollama pull llama3:8b
```

### Frontend Can't Connect to Backend

- Ensure backend is running on port 8000
- Check CORS settings in `main.py` include your frontend URL
- Verify no firewall blocking localhost ports

---

## License

MIT License - See [LICENSE](LICENSE) file for details.
