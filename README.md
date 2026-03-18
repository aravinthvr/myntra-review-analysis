# ◈ ReviewIQ Pro: Unified Retail Intelligence System

**ReviewIQ Pro** is a high-performance, full-stack intelligence dashboard designed to ingest, analyze, and visualize thousands of customer reviews with verified accuracy. Built for product analysts and e-commerce managers, it uses a **Map-Reduce AI Architecture** to process large datasets (2,000+ reviews) without losing context or hallucinating facts.

---

## ✨ Key Features

- **Deep Node Analysis** — Recursively scans HTML nodes to identify specific reviewer identities and pair them with their feedback.
- **Verifiable Intelligence** — Every praise and critical issue is attributed to a specific "Verified Reviewer" name found in the source HTML.
- **Map-Reduce Engine** — Processes high-volume data in parallel batches of 60 reviews to ensure 100% data coverage and sentiment accuracy.
- **Global Market Dashboard** — Real-time KPIs including Market Reach, Global Sentiment (NPS Weight), and Systemic Risk tracking.
- **Product Leaderboard** — Automatically identifies "Market Leaders" and "Critical Failure" products based on your total scan history.
- **Persistence Layer** — Fully integrated with **Google Firebase (Firestore)** to track analysis history and long-term performance trends.

---

## 🏗️ Technical Stack

| Layer | Technology |
|---|---|
| **Frontend** | Streamlit (Premium Dark Theme) |
| **Intelligence** | Google Gemini 2.5 Flash (LLM) |
| **Data Extraction** | BeautifulSoup4 (HTML Parsing) |
| **Database** | Google Firebase / Firestore |
| **Visualization** | Plotly Express & Pandas |

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- A Google AI (Gemini) API Key
- A Firebase Service Account Key (`serviceAccountKey.json`)

### 2. Installation
```bash
# Clone the repository
git clone [https://github.com/yourusername/review-iq-pro.git](https://github.com/yourusername/review-iq-pro.git)
cd review-iq-pro

# Install dependencies
pip install -r requirements.txt
