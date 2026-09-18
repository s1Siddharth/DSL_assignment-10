<div align="center">

# 🛡️ OmniShield AI
### Autonomous Network Intrusion Detection & Threat Protection Platform

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3%2B-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**Real-time ML-powered network traffic analysis, anomaly detection & threat alerting — all in one sleek dark-mode dashboard.**

[Live Demo](#-quick-start) • [Features](#-features) • [Architecture](#-architecture) • [Team](#-team)

</div>

---

## 📌 Overview

**OmniShield AI** is an end-to-end network intrusion detection system (NIDS) built as a college DSL project. It lets you:

1. **Upload** a labeled network traffic CSV (KDD Cup 99 format, NSL-KDD, or custom)
2. **Train** a Random Forest classifier directly from the browser
3. **Analyze** individual packets or run batch analysis on new CSVs
4. **Monitor** threats in real-time on an auto-refreshing dashboard
5. **Get Alerts** with severity levels (CRITICAL / HIGH / MEDIUM / LOW)
6. **Visualize** attack trends, confusion matrices, feature importance & more

---

## 👥 Team

> DSL Mini-Project · Academic Year 2026

| Name | Roll No. | Contribution |
|---|---|---|
| **Siddharth Jadhav** | 17 | Backend API, ML Pipeline, Database Design |
| **Krish Chorghe** | 09 | Frontend UI, Charts, SPA Router |
| **Soham Chindarkar** | 08 | Data Preprocessing, Testing, Documentation |

---

## ✨ Features

| Module | Capabilities |
|---|---|
| 🗄️ **Datasets** | Drag-and-drop CSV upload, column preview, dataset management |
| 🤖 **ML Models** | One-click Random Forest training, feature importance, confusion matrix, per-class metrics |
| 🔍 **Analyze** | Single-packet manual analysis + batch CSV inference |
| 📊 **Dashboard** | Live stats (auto-refresh every 15s), security score ring, attack trend chart |
| 📈 **Analytics** | Time-period filter (7/14/30/90 days), distribution charts, risk heatmap |
| 🚨 **Alerts** | Auto-generated severity alerts, acknowledge/resolve workflow |
| 📋 **History** | Full paginated activity log with search & filters |
| 📄 **Reports** | Summary statistics with export-ready layout |

---

## 🗂️ Architecture

```
omnishield-ai/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration classes (dev/prod)
│   ├── extensions.py        # DB, SQLAlchemy setup
│   ├── ml/                  # ML training & inference engine
│   ├── models/              # SQLAlchemy ORM models
│   ├── routes/              # REST API blueprint routes
│   ├── services/            # Business logic layer
│   ├── static/
│   │   ├── css/style.css    # Dark-mode design system
│   │   └── js/
│   │       ├── app.js       # SPA router + Chart.js helpers
│   │       └── pages/       # Per-page JS modules
│   └── templates/
│       ├── index.html       # Main SPA shell
│       └── landing.html     # Public landing page
├── models/
│   ├── trained/             # Saved .joblib model files (gitignored)
│   └── metadata/            # Model metadata JSON (gitignored)
├── uploads/                 # User-uploaded CSVs (gitignored)
├── instance/                # SQLite DB (gitignored)
├── tests/                   # pytest test suite
├── run.py                   # App entry point
├── pyproject.toml           # Project metadata & dependencies
└── .env.example             # Environment variable template
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- pip

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/omnishield-ai.git
cd omnishield-ai
```

### 2. Set up virtual environment
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -e .
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env and set your SECRET_KEY
```

### 5. Run the app
```bash
python run.py
```

Open **http://127.0.0.1:5000** in your browser. 🎉

---

## 📊 Supported Dataset Formats

OmniShield AI works with any **CSV file** containing network traffic features. Tested datasets:

| Dataset | Format | Notes |
|---|---|---|
| KDD Cup 99 | CSV | Classic IDS benchmark |
| NSL-KDD | CSV | Improved version of KDD 99 |
| Custom | CSV | Must include a labeled `label` column |

The app auto-detects column names and maps them to features during training.

---

## 🧠 ML Pipeline

```
CSV Upload → Feature Engineering → Train/Test Split (80/20)
    → Random Forest Classifier (100 estimators)
        → Accuracy / Precision / Recall / F1
            → Save model → Deploy for real-time inference
```

**Output Classes:** `normal` · `attack` · `suspicious`

---

## 🖥️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Flask 3.0, SQLAlchemy |
| ML Engine | scikit-learn, pandas, numpy, joblib |
| Frontend | Vanilla JS (SPA), Chart.js 4.4, chartjs-plugin-datalabels |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Styling | Pure CSS with CSS custom properties (dark-mode design system) |

---

## 📝 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">
Made with ❤️ for DSL Mini-Project · OmniShield AI Team · 2026
</div>
