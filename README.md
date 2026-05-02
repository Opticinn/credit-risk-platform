# Credit Risk Scoring Platform
> XGBoost + SHAP + RAG + Gemini Flash | Explainable AI Credit Decisioning

---

## ⚡ Quick Start (Windows + VSCode)

### 1. Clone / buat folder project
```
credit-risk-platform/
```

### 2. Buat & aktifkan virtual environment
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup environment variables
```bash
copy .env.example .env
# Buka .env dan isi:
# - GEMINI_API_KEY  → https://aistudio.google.com/app/apikey
# - SECRET_KEY      → string random panjang
```

### 5. Jalankan Docker (PostgreSQL + Redis)
```bash
docker compose up -d
```

### 6. Jalankan FastAPI
```bash
uvicorn app.main:app --reload
```

Buka browser: http://localhost:8000/docs

---

## 🗂️ Project Structure
```
credit-risk-platform/
├── app/
│   ├── api/           # Route handlers (per phase)
│   ├── services/      # Business logic
│   ├── models/        # SQLAlchemy ORM models
│   ├── config.py      # Settings dari .env
│   ├── database.py    # DB engine & session
│   └── main.py        # FastAPI app entrypoint
├── portals/
│   ├── internal/      # Loan officer dashboard
│   └── external/      # Applicant portal
├── data/              # ChromaDB, MLflow, datasets (gitignored)
├── .github/workflows/ # GitHub Actions CI/CD
├── docker-compose.yml # PostgreSQL + Redis
├── requirements.txt
└── .env.example
```

---

## 🚀 Development Phases

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Data & API (FastAPI, PostgreSQL, JWT) | 🔜 |
| 2 | ML Pipeline (XGBoost, SHAP, MLflow) | 🔜 |
| 3 | RAG + Gemini Flash (ChromaDB, LangChain) | 🔜 |
| 4 | Dual Portal (Internal + External UI) | 🔜 |
| 5 | MLOps (Evidently, Grafana, Telegram) | 🔜 |
| 6 | Polish & Deploy | 🔜 |

---

## 🔑 API Keys yang Dibutuhkan
- **Gemini API** (gratis): https://aistudio.google.com/app/apikey
- **Telegram Bot** (optional): @BotFather di Telegram
