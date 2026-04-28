# 🤖 ChatBot SaaS

A multi-tenant AI chatbot platform that lets you embed a smart support widget on any website. Built with Django Channels (WebSockets), Google Gemini (LangChain), pgvector RAG, Kafka, and a Next.js dashboard.

---

## 📸 Screenshots

### Dashboard
![Dashboard](<img width="1456" height="819" alt="image" src="https://github.com/user-attachments/assets/d275db13-d543-4e09-92b2-cd0adb4df725" />
)

### Website Detail & Embed Script
![Website Detail](screenshot_website_detail.png)

### Edit Website & Visitor Info Fields
![Edit Website](screenshot_edit_website.png)

### Chat Session View (Agent Side)
![Chat Session](screenshot_chat_session.png)
![Chat Session 2](screenshot_chat_session2.png)

### Live Chat Widget (Visitor Side)
![Widget](screenshot_widget.png)

---

## ✨ Features

- **Multi-tenant SaaS** — Each user account manages multiple websites independently
- **Embeddable Chat Widget** — Inject a `<script>` tag into any site to activate the chatbot
- **AI Agent (Google Gemini)** — Powered by LangChain ReAct agent with tool use (knowledge base lookup, escalation, etc.)
- **RAG Knowledge Base** — Upload documents (PDF, text) per website; answers are grounded via pgvector similarity search
- **Human Escalation** — AI detects when a visitor wants a human and seamlessly hands off via WebSocket to a live agent
- **Visitor Info Collection** — Configurable pre-chat fields (name, email, custom) collected conversationally before connecting to an agent
- **Real-time Chat** — Django Channels + Redis channel layer for full-duplex WebSocket communication
- **Chat Session Management** — View, manage, end, and delete sessions from the dashboard
- **Analytics** — Track sessions, messages, and visitor activity per website
- **Google OAuth** — Social login support
- **Kafka Pipeline** — Document uploads are processed asynchronously via Kafka consumer
- **Docker Compose** — Full stack orchestration (Django/Daphne, Redis, Kafka, Nginx)

---

## 🏗️ Architecture

```
Visitor Browser                  Dashboard (Next.js :3000)
      │                                    │
      │  WebSocket (ws://)                 │  REST API (HTTP)
      ▼                                    ▼
  widget.js  ────────────────►  Django / Daphne ASGI (:8000)
                                           │
                          ┌────────────────┼────────────────┐
                          ▼                ▼                ▼
                    Django Channels    REST API        Celery Worker
                    (consumers.py)   (DRF views)      (async tasks)
                          │                │
                          ▼                ▼
                      Redis          PostgreSQL + pgvector
                   (channel layer)   (sessions, messages,
                                      document embeddings)
                          │
                          ▼
                   LangChain Agent
                   (Google Gemini)
                          │
                          ▼
                   RAG (pgvector)  ◄──  Kafka Consumer
                                        (document ingestion)
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 4+, Django REST Framework, Django Channels |
| ASGI Server | Daphne |
| AI / LLM | Google Gemini via LangChain (`langchain-google-genai`) |
| Vector Search | pgvector (PostgreSQL extension) |
| Message Broker | Apache Kafka (KRaft mode) |
| Task Queue | Celery + Redis |
| Database | PostgreSQL (+ Supabase support) |
| Cache / Channels | Redis |
| Frontend Dashboard | Next.js (React) |
| Widget | Vanilla JS (`widget.js`) |
| Auth | JWT (SimpleJWT) + Google OAuth2 |
| Reverse Proxy | Nginx |
| Containerization | Docker + Docker Compose |

---

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose
- A Google Gemini API key
- (Optional) Supabase project for hosted Postgres + pgvector

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd chatbot
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
# Django
SECRET_KEY=your-super-secret-key-change-this-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database
DB_NAME=chatbot_db
DB_USER=postgres
DB_PASSWORD=postgres123
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379

# Google Gemini
GOOGLE_API_KEY=your-gemini-api-key

# Google OAuth (optional)
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=...
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=...
```

### 3. Start with Docker Compose

```bash
docker-compose up --build
```

This starts:
- `web` — Django app on port `8000` (via Daphne ASGI)
- `redis` — Redis on port `6379`
- `kafka` — Kafka broker on port `9092`
- `kafka-consumer` — Document ingestion worker
- `nginx` — Reverse proxy on port `80`

### 4. Run the Next.js dashboard

The dashboard is a separate Next.js project. In a new terminal:

```bash
cd frontend   # or wherever your Next.js app lives
npm install
npm run dev
# Runs on http://localhost:3000
```

---

## 📋 Usage

### 1. Register & Log in

Sign up at `http://localhost:3000`. JWT tokens are used for authentication.

### 2. Create a Website

Click **Create Website** from the dashboard. Enter your site's name and domain.

### 3. Configure Visitor Info Fields

In **Edit Website**, add custom fields (e.g., Full Name, Email) that the bot will collect conversationally before escalating to a human agent.

### 4. Upload Documents to the Knowledge Base

Navigate to **Documents** and upload PDFs or text files. They are ingested via Kafka and chunked + embedded into pgvector for RAG-powered answers.

### 5. Embed the Widget

Copy the embed script from your website's detail page:

```html
<script
  src="http://localhost:8000/static/widget.js"
  data-api-key="your-api-key"
  data-ws-host="localhost:8000">
</script>
```

Paste it into the `<body>` of any webpage. The chat widget will appear in the bottom-right corner.

### 6. Live Agent Support

When a visitor requests a human (or the AI detects escalation intent), the session is flagged. An authenticated agent can join via **Live Support** in the dashboard and chat in real time over WebSocket.

---

## 📁 Project Structure

```
chatbot/
├── chatbot/            # Django project settings, ASGI, URLs, Celery
├── accounts/           # TenantUser model, JWT auth, Google OAuth
├── websites/           # Website model, API key, visitor info fields
├── chat/
│   ├── consumers.py    # WebSocket consumer (visitor + agent logic)
│   ├── agent.py        # LangChain ReAct agent + Gemini LLM
│   ├── models.py       # ChatSession, Message, RequestCallback
│   └── middleware.py   # JWT auth middleware for WebSocket
├── knowledge_base/
│   ├── models.py       # Document, DocumentChunk models
│   ├── rag.py          # pgvector similarity search
│   ├── tasks.py        # Celery tasks for document processing
│   └── kafka_consumer.py # Kafka consumer for async ingestion
├── analytics/          # Session & message analytics views
├── static/widget.js    # Embeddable chat widget (vanilla JS)
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
└── requirements.txt
```

---

## 🔌 API Overview

All REST endpoints are prefixed with `/api/`. Authentication requires a JWT Bearer token.

| Resource | Endpoints |
|---|---|
| Auth | `POST /api/auth/register/`, `POST /api/auth/login/`, `POST /api/auth/token/refresh/` |
| Websites | `GET/POST /api/websites/`, `GET/PUT/DELETE /api/websites/<id>/` |
| Documents | `GET/POST /api/knowledge-base/documents/` |
| Chat Sessions | `GET /api/chat/sessions/`, `GET /api/chat/sessions/<id>/` |
| Analytics | `GET /api/analytics/` |

**WebSocket URL:**
```
ws://localhost:8000/ws/chat/<website_id>/<session_id>/
```

---

## ⚙️ Environment Variables Reference

| Variable | Description | Required |
|---|---|---|
| `SECRET_KEY` | Django secret key | ✅ |
| `DEBUG` | Debug mode (`True`/`False`) | ✅ |
| `GOOGLE_API_KEY` | Google Gemini API key | ✅ |
| `DB_*` | PostgreSQL connection details | ✅ |
| `REDIS_URL` | Redis connection URL | ✅ |
| `SOCIAL_AUTH_GOOGLE_OAUTH2_KEY` | Google OAuth client ID | Optional |
| `CORS_ALLOW_ALL_ORIGINS` | Allow all CORS origins | Optional |

---

## 🧑‍💻 Development Notes

- The Django app runs with **Daphne** (ASGI) to support WebSockets. Do not use `manage.py runserver` in production.
- Kafka runs in **KRaft mode** (no ZooKeeper required).
- The `kafka-consumer` container automatically creates the `document-upload` topic on startup.
- pgvector must be enabled in your PostgreSQL database: `CREATE EXTENSION IF NOT EXISTS vector;`
- If using Supabase, enable the pgvector extension from the Supabase dashboard.

---

## 📄 License

MIT — feel free to use, fork, and extend.
