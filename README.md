# 🏦 Credit Risk Platform

> **Explainable AI Credit Decisioning** — XGBoost + SHAP + RAG + Qwen2.5 + Multi-Agent LangGraph

[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Containerized-blue?style=flat-square&logo=docker)](https://docker.com)
[![XGBoost](https://img.shields.io/badge/XGBoost-AUC_0.9465-orange?style=flat-square)](https://xgboost.ai)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-purple?style=flat-square)](https://langchain-ai.github.io/langgraph)

> 🇮🇩 **Language Note:** All user-facing content — including portal UI, LLM responses, AI chat explanations, credit decision narratives, and policy documents — is delivered in **Bahasa Indonesia**, as this platform is designed for the Indonesian banking market.

---

## 📸 Screenshots

### Applicant Portal (External)
![External Portal](docs/screenshots/external.webp)

### Loan Officer Dashboard (Internal)
![Internal Portal](docs/screenshots/internal.webp)

---

## 🎯 About

An end-to-end **Explainable AI credit risk decisioning platform** that combines traditional machine learning with modern LLM technology. Every credit decision is transparently explainable to applicants in natural language.

### Problem Statement
Traditional banks often approve or reject credit without clear explanations. This platform provides:
- **Instant decisions** powered by ML (< 3 seconds)
- **Transparent explanations** of why applications are approved or rejected
- **Multi-agent analysis** for more comprehensive decision-making
- **Automated monitoring** to detect model drift over time

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│     Applicant Portal (External)   Loan Officer Dashboard     │
└──────────────────┬──────────────────────┬───────────────────┘
                   │                      │
┌──────────────────▼──────────────────────▼───────────────────┐
│                      FastAPI Backend                         │
│    /auth  /score  /chat  /agent  /officer  /monitor         │
└──────┬──────────┬────────────┬──────────┬────────────────────┘
       │          │            │          │
   ┌───▼───┐  ┌──▼───┐  ┌────▼────┐  ┌──▼──────┐
   │XGBoost│  │ RAG  │  │LangGraph│  │Evidently│
   │+ SHAP │  │+Qwen │  │ Agents  │  │Telegram │
   └───────┘  └──────┘  └─────────┘  └─────────┘
       │          │
   ┌───▼──────────▼───────────────────────────────┐
   │               Data Layer                      │
   │   PostgreSQL   Redis   ChromaDB   MLflow      │
   └───────────────────────────────────────────────┘
```

---

## ✨ Key Features

### 🤖 ML Scoring Engine
- **XGBoost** model with AUC of **0.9465**
- **SHAP** explainability — every decision factor is quantified
- Trained on 32,000+ real credit applications
- **MLflow** experiment tracking and model versioning

### 🧠 RAG + Local LLM
- **ChromaDB** vector database for semantic search
- **Qwen2.5 7B** via Ollama — runs locally, free, and private
- Natural language explanations delivered in **Bahasa Indonesia**
- Credit policy documents used as AI reference context

### 🤝 Multi-Agent System (LangGraph)
A 4-agent pipeline running sequentially:
```
Risk Analyst → Policy Checker → Fraud Detector → Report Writer
```
- **Risk Analyst** — ML scoring + SHAP analysis
- **Policy Checker** — policy validation via RAG
- **Fraud Detector** — rule-based anomaly detection
- **Report Writer** — final decision + natural language explanation

### 🖥️ Dual Portal
- **Applicant Portal** — submit applications, view results, chat with AI
- **Loan Officer Dashboard** — manage applications, override decisions, AI analysis

### 📊 Monitoring & Alerting
- **Drift Detection** using PSI (Population Stability Index)
- **Telegram Bot** for real-time notifications
- Health check endpoints for all components
- Automated daily reports

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend API** | FastAPI, Uvicorn, SQLAlchemy |
| **Database** | PostgreSQL, Redis |
| **ML** | XGBoost, SHAP, Scikit-learn, MLflow |
| **LLM** | Qwen2.5 7B via Ollama (local) |
| **Vector DB** | ChromaDB + Sentence Transformers |
| **Agentic AI** | LangGraph, LangChain |
| **Monitoring** | Evidently AI, Telegram Bot |
| **DevOps** | Docker, Docker Compose |
| **Auth** | JWT (python-jose) + bcrypt |
| **Frontend** | Vanilla HTML, CSS, JavaScript |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker Desktop
- [Ollama](https://ollama.com) with `qwen2.5:7b` model

### 1. Clone Repository
```bash
git clone https://github.com/Opticinn/credit-risk-platform.git
cd credit-risk-platform
```

### 2. Setup Environment
```bash
# Copy environment template
copy .env.example .env

# Fill in .env:
# - SECRET_KEY        → any long random string
# - TELEGRAM_BOT_TOKEN → from @BotFather on Telegram
# - TELEGRAM_CHAT_ID   → from getUpdates API
```

### 3. Install Dependencies
```bash
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
```

### 4. Download Dataset & Train Model
```bash
# Download dataset from Kaggle
python data/download_dataset.py

# Train XGBoost model (~3 minutes)
python data/train_model.py
```

### 5. Pull Local LLM
```bash
ollama pull qwen2.5:7b
```

### 6. Run with Docker
```bash
docker compose up
```

### 7. Open Portals
```bash
python -m http.server 5500
```

| Portal | URL |
|--------|-----|
| Applicant Portal | http://localhost:5500/portals/external/index.html |
| Loan Officer Dashboard | http://localhost:5500/portals/internal/index.html |
| API Documentation | http://localhost:8000/docs |

---

## 📁 Project Structure

```
credit-risk-platform/
├── app/
│   ├── api/                    # Route handlers
│   │   ├── auth.py             # Register, login, JWT
│   │   ├── score.py            # Credit scoring endpoint
│   │   ├── chat.py             # AI chat endpoint
│   │   ├── officer.py          # Loan officer API
│   │   ├── monitor.py          # Monitoring & health check
│   │   └── agent.py            # Multi-agent endpoint
│   ├── models/                 # SQLAlchemy ORM models
│   ├── services/
│   │   ├── ml/                 # XGBoost inference service
│   │   ├── rag/                # ChromaDB + Qwen2.5 RAG
│   │   ├── agents/             # LangGraph multi-agent system
│   │   │   ├── state.py        # Shared agent state
│   │   │   ├── agents.py       # 4 specialized agents
│   │   │   └── graph.py        # LangGraph workflow
│   │   └── monitoring/         # Drift detection + Telegram
│   ├── config.py
│   ├── database.py
│   └── main.py
├── data/
│   ├── models/                 # Trained ML artifacts (.pkl)
│   ├── policy_docs/            # Credit policy documents (.md)
│   ├── download_dataset.py
│   └── train_model.py
├── portals/
│   ├── external/               # Applicant portal (HTML/CSS/JS)
│   └── internal/               # Loan officer dashboard
├── docs/screenshots/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## 🔌 API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login, receive JWT token |
| GET | `/auth/me` | Get current user profile |

### Credit Scoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/score/apply` | Submit credit application |
| GET | `/score/history` | Application history |
| GET | `/score/{id}` | Single application detail |

### AI Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/explain/{id}` | Explain credit decision |
| POST | `/chat/ask` | Ask any credit-related question |

### Multi-Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agent/decide` | Run full multi-agent pipeline |

### Monitoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/monitor/health` | Health check all components |
| GET | `/monitor/drift` | Run drift detection |
| GET | `/monitor/stats/daily` | Daily stats + Telegram report |
| POST | `/monitor/alert/test` | Test Telegram alert |

---

## 📊 Model Performance

| Metric | Score |
|--------|-------|
| **ROC-AUC** | **0.9465** |
| Precision | 0.8271 |
| Recall | 0.7811 |
| F1-Score | 0.8035 |

> Trained on [Credit Risk Dataset](https://www.kaggle.com/datasets/laotse/credit-risk-dataset) — 32,574 records after preprocessing.

---

## 🔐 Role-Based Access Control

| Role | Access |
|------|--------|
| `applicant` | Submit applications, view own results, AI chat |
| `loan_officer` | All applications, override decisions, dashboard |
| `admin` | Full access to all features |

---

## 📱 Telegram Monitoring Alerts

The bot automatically sends notifications for:
- 🚀 Server startup
- 🚨 Model drift detected
- 📋 Daily summary report
- 🔴 Critical errors

---

## 🗺️ Roadmap

- [x] Phase 1 — FastAPI + PostgreSQL + JWT Auth
- [x] Phase 2 — XGBoost + SHAP + MLflow
- [x] Phase 3 — RAG + Qwen2.5 + AI Chat
- [x] Phase 4 — Dual Portal UI
- [x] Phase 5 — Monitoring + Telegram Alerts
- [x] Phase 6 — Docker Containerization
- [x] Phase 7 — Multi-Agent LangGraph
- [ ] Phase 8 — Deploy to GCP Cloud Run
- [ ] Phase 9 — CI/CD Pipeline (GitHub Actions)

---

## 👨‍💻 Author

**Rafli Fauzi**
- GitHub: [@Opticinn](https://github.com/Opticinn)

---

## 📄 License

MIT License — free to use for learning and portfolio purposes.