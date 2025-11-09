# Balance-Sheet Chat Assistant – Technical Report

## 1. Introduction

This project implements a **ChatGPT-style assistant for balance-sheet analysts and top management**, designed to work on **publicly available balance sheet / annual report PDFs**.

The system:

- Lets a user **upload a balance-sheet/annual report PDF** (e.g. Reliance Industries’ consolidated report).
- Parses and extracts **key financial metrics** (revenue, net profit, total assets, total liabilities) across years.
- Uses **Retrieval-Augmented Generation (RAG)** over the full PDF text to answer nuanced questions.
- Supports **role-aware responses** (CEO vs Analyst vs Management).
- Provides **on-demand visualizations** (line/bar/pie charts) when the user asks to “show/visualize/plot” metrics.
- Is **publicly deployed** with:
  - Backend: FastAPI on Render
  - Frontend: React + Vite on Vercel

The goal is to simulate how an internal “Balance-Sheet Copilot” could help analysts and senior leaders quickly understand a company’s financial performance using public balance sheets.

---

## 2. Problem Statement & Objectives

### 2.1 Assignment problem statement (rephrased)

Given a public company’s balance sheet / annual report, build a **ChatGPT-like assistant** that:

- Allows **analysts** and **top management** to ask questions in natural language about:
  - sales, growth, assets, liabilities, profits, etc.
  - narrative explanations (litigation, revenue recognition, risks, etc.).
- Can **quickly review multiple past balance sheets**.
- Uses **publicly available balance sheets** as its primary data source.
- Supports **role-based views**:
  - Analysts and BU heads see data for their company.
  - Group-level leadership (e.g. promoter family) sees data across all group companies.
- Produces a complete, functional product that:
  - Is **publicly deployed**
  - Has a clear **technical design & documentation**
  - Emphasizes **data security** and reasonable **latency**.

### 2.2 Project objectives

This implementation focuses on:

1. Building a working **end-to-end system**:
   - PDF upload → parsing → metrics extraction → RAG → chat answers → optional charts.
2. Ensuring **answers are grounded** in the uploaded document only (no hallucinated internet data).
3. Demonstrating **role-aware behaviour** (CEO vs Analyst) in the chat responses.
4. Supporting **multiple documents** (recent balance sheets) in a single UI and allowing quick switching.
5. Providing a **public deployment** plus **Dockerization** for container readiness.

Full, production-grade authentication and fine-grained per-company RBAC is considered **future work**, but the data model and architecture are designed to support it.

---

## 3. System Overview

At a high level, the system consists of:

- **Frontend (React + Vite, deployed on Vercel)**
  - Startup screen:
    - Upload a new PDF balance sheet.
    - Or choose from “Recent Balance Sheets” already processed.
    - Select user role (CEO / Analyst / Management).
  - Chat interface:
    - Chat with an assistant about the selected document.
    - View **inline charts** when explicitly requested.
    - Switch quickly between documents (“Other Reports” panel).

- **Backend (FastAPI, deployed on Render)**
  - Endpoints:
    - `POST /upload/balance-sheet` – upload & process a PDF.
    - `GET /documents` – list processed financial documents with summary metrics.
    - `POST /chat/query` – answer questions based on a given `document_id` (or demo mode company).
  - Responsibilities:
    - Classify PDFs as **financial vs non-financial**.
    - Parse PDFs, extract key metrics, and store them into a database.
    - Chunk and embed the full text for RAG.
    - Build a context (structured metrics + retrieved chunks) and call the LLM (Gemini) to answer.
    - Optionally generate **chart configuration** for visualization.

- **Database (SQLite)**
  - Stores:
    - Documents and their metadata.
    - Extracted financial metrics.
    - Text chunks and embeddings for retrieval.

- **LLM & Embeddings (Gemini API)**
  - Used for:
    - PDF classification.
    - Metrics extraction.
    - Embedding generation for RAG.
    - Answer generation.
    - Chart planning (deciding chart type and metrics to visualize).

---

## 4. Architecture

### 4.1 Tech stack

**Backend**

- Python 3.x
- FastAPI
- Uvicorn
- SQLAlchemy + SQLite
- pdfplumber (PDF parsing)
- google-generativeai + google-ai-generativelanguage (Gemini)
- Pydantic & pydantic-settings
- pdfminer.six, pypdfium2 (PDF/text tooling)
- python-multipart (file uploads)

**Frontend**

- React (with Vite)
- Axios (HTTP client)
- Recharts (charts rendering)
- Modern React hooks & functional components

**Infrastructure**

- Backend: Render (free tier Web Service)
- Frontend: Vercel
- Dockerfiles for both `/backend` and `/frontend` for container builds.

### 4.2 Backend modules & routers

- `app/main.py`
  - Creates FastAPI app
  - Initializes database (creates tables)
  - Sets CORS
  - Includes routers:
    - `/chat` – chat interface
    - `/upload` – PDF upload & parsing
    - `/documents` – document listing
  - Health endpoint: `/health`

- `app/models.py`
  - `Document`: uploaded file, company & year metadata, hash, timestamps, classification flags.
  - `FinancialMetric`: metric_name, value, year, linked to a `Document`.
  - `DocumentChunk`: per-document text chunks + embeddings for RAG.

- `app/schemas.py`
  - Pydantic models for:
    - `UploadResponse`
    - `ChatRequest` / `ChatResponse`
    - `DocumentSummary` & `DocumentListResponse`
    - `ChartData` (with chart_type, years, series)

- `app/routers/upload.py`
  - `POST /upload/balance-sheet`
    - Accepts `multipart/form-data` with a PDF file.
    - Classifies the PDF as financial / non-financial.
    - Rejects non-financial PDFs with a clear error.
    - For financial PDFs:
      - Creates `Document` entry.
      - Parses the PDF.
      - Extracts metrics & chunks.
      - Populates DB.

- `app/routers/documents.py`
  - `GET /documents`
    - Returns recent financial documents (`is_financial_report == True`) with:
      - ID, company_name, fiscal_year, filename, created_at.
      - Latest year and its revenue/net_profit.
  - The frontend:
    - Shows “Recent Balance Sheets” on the startup screen.
    - Shows “Other Reports” in the chat view for quick switching.

- `app/routers/chat.py`
  - `POST /chat/query`
    - Request includes:
      - `document_id` (for document-based queries)
      - `role` (CEO / Analyst / Management)
      - `messages` (chat history; final one is the user question)
    - Builds `metrics_by_year` for that document.
    - Uses RAG to retrieve relevant chunks.
    - Crafts a role-aware system prompt.
    - Calls LLM to generate answer text.
    - Optionally invokes chart-planner to return `chart_data` when user explicitly asks to “show/plot/visualize/chart” something.

- `app/parsing.py`
  - Extracts text from PDF using pdfplumber.
  - Uses Gemini to:
    - Classify PDF as financial / non-financial.
    - Extract:
      - Company name
      - Fiscal year
      - Metrics:
        - revenue
        - net_profit
        - total_assets
        - total_liabilities
      - per year.
  - Saves metrics in `FinancialMetric`.
  - Chunks the full text and calls embedding function.
  - Populates `DocumentChunk` table with text and embeddings.
  - Sets `processed_at` timestamp on `Document`.

- `app/llm.py`
  - `call_llm(system_prompt, user_prompt)`:
    - Wrapper around Gemini text model.
  - `embed_texts(text_list)`:
    - Wrapper around Gemini embedding model.
    - Returns normalized float vectors.

- `app/retrieval.py`
  - `_cosine_similarity()`
  - `retrieve_relevant_chunks(document_id, question, db, top_k=5)`:
    - Embeds the question.
    - Loads all chunks/embeddings for the document.
    - Computes similarity and returns top-k text chunks.

- `app/charts.py`
  - `build_metrics_summary_for_planner(metrics_by_year)`:
    - Summarizes available metrics for each year for the planner.
  - `plan_chart_config(user_question, metrics_by_year)`:
    - Uses LLM to decide whether to show a chart and which chart type/metrics.
    - Returns JSON-like config:
      - `wants_chart`
      - `chart_type`: "line" | "bar" | "pie" | "none"
      - `metrics`: list of metric names (e.g., ["revenue", "net_profit"])
      - `x_axis`, `aggregation`.
  - `build_chart_data_from_plan(plan, metrics_by_year)`:
    - Uses the plan to build `chart_data`:
      - For `line`/`bar`: `years` + `series`.
      - For `pie`: single year (latest) composition.

---

## 5. Data Flow

### 5.1 Upload and classification

1. User selects a PDF in the frontend and clicks **Upload**.
2. Frontend sends `POST /upload/balance-sheet` with `multipart/form-data`.
3. Backend:
   - Temporarily saves the PDF file.
   - Extracts text from the first few pages.
   - Calls Gemini with a classification prompt:
     - Is this a **financial report / balance sheet / annual report**, or something else?
   - If classification indicates **non-financial**:
     - Deletes the file.
     - Returns `400` with a human-readable reason (e.g., “This looks like a marksheet, not a financial report.”)
   - If **financial**:
     - Calculates a document hash to detect duplicates.
     - Creates a `Document` row:
       - `filename`, `storage_path`, `company_name` (from LLM), `fiscal_year`, `hash`, `created_at`, etc.
     - Proceeds to parsing and metrics extraction.

### 5.2 Parsing, metrics, and chunking

1. Backend parses the PDF with pdfplumber:
   - Extracts text page by page.
2. Calls Gemini with carefully designed prompts to extract:
   - Company name (if not already captured).
   - Fiscal year (e.g., “Year ended 31 March 2024”).
   - Financial metrics per year:
     - revenue (top line)
     - net_profit
     - total_assets
     - total_liabilities
3. Converts numeric values into standard units (e.g., crores/millions → absolute numbers).
4. Stores metrics into `FinancialMetric` table keyed by `document_id` and `year`.
5. For RAG:
   - Concatenates the full text.
   - Splits into chunks (e.g., character-based with some overlap) per page.
   - Calls `embed_texts()` on all chunks to get embeddings.
   - Stores each chunk + embedding into `DocumentChunk`.

### 5.3 Listing documents

- `GET /documents`:
  - Returns all financial documents (`is_financial_report == True`) with:
    - ID, company_name, fiscal_year, filename, created_at.
    - Latest year and its revenue/net_profit.
  - The frontend:
    - Shows “Recent Balance Sheets” on the startup screen.
    - Shows “Other Reports” in the chat view for quick switching.

### 5.4 Chat with RAG and metrics

When user asks a question via chat:

1. Frontend sends `POST /chat/query` with:
   - `document_id`
   - `role` (CEO/Analyst/Management)
   - `messages` (chat history; final one is the user question).

2. Backend:
   - Reads `document_id` and loads:
     - All metrics for that document → builds `metrics_by_year`:
       - e.g. `{2023: {"revenue": ..., "net_profit": ...}, 2024: {...}}`
   - Checks if the latest user message is a greeting (e.g., “hi”, “hello”):
     - If yes → returns a friendly greeting, no metrics needed.
   - Calls `retrieve_relevant_chunks()`:
     - Embeds the user question.
     - Computes cosine similarity with all stored chunk embeddings.
     - Returns the top-k most relevant text excerpts.

3. A **system prompt** is then built:
   - Includes role guidelines:
     - CEO → high-level, concise, insight-focused.
     - Analyst → detailed metrics, explanations, and caveats.
   - Includes:
     - A tabular summary of `metrics_by_year`.
     - The retrieved text chunks (as context).
   - Instructs LLM:
     - Only answer based on provided metrics and excerpts.
     - If information is not present, say so.
     - Do not answer from general world knowledge.

4. Backend calls `call_llm(system_prompt, user_prompt)` and gets:
   - A natural language `answer`.

5. For visualization:
   - Backend checks if the user explicitly asked to **show/plot/visualize/chart/draw**:
     - If **no** → `chart_data = None`.
     - If **yes** → calls `plan_chart_config(user_question, metrics_by_year)`:
       - Asks LLM to decide:
         - `wants_chart` (true/false)
         - `chart_type` (line, bar, pie, none)
         - `metrics` (e.g. `["revenue", "net_profit"]`)
         - `aggregation` (e.g. "none" or "latest_year")
       - Special case: if user asks for a “flow chart / flowchart”, planner always sets `chart_type = "none"` (we return textual steps only).
   - If planner returns `wants_chart = true`:
     - `build_chart_data_from_plan()` constructs a `chart_data` payload.
   - Otherwise:
     - `chart_data = None`.

6. Backend returns `ChatResponse`:

```json
{
  "answer": "Here is the trend for revenue and net profit over the last three years...",
  "chart_data": {
    "chart_type": "line",
    "years": [2022, 2023, 2024],
    "series": [
      { "label": "Revenue", "values": [700000, 800000, 900000] },
      { "label": "Net Profit", "values": [60000, 65000, 70000] }
      ]
}
```

(or `"chart_data": null` if not requested or not appropriate).

### 5.5 Frontend rendering

- The chat UI stores messages with optional `chartData`.
- When an assistant message includes `chartData`, a `MetricsChart` component renders:
  - For `chart_type = "line"` → LineChart (trends).
  - For `chart_type = "bar"` → BarChart (comparisons).
  - For `chart_type = "pie"` → PieChart (composition in the latest year).
- Charts are displayed **inline below the assistant message** that triggered them.

---

## 6. Role & Access Model

The original assignment describes a multi-tenant scenario (e.g., CEO of Jio can only see Jio data, Ambani family sees all companies). Implementing full auth & RBAC with user accounts is beyond the timeline, so this prototype models roles in a **simplified but extensible** way:

- The frontend allows the user to pick a **role**:
  - CEO
  - Analyst
  - Management (or similar)
- This `role` is passed to the backend with each chat request.
- Backend uses role to:
  - Adjust the **tone & depth** in the system prompt:
    - CEO → strategic, concise, highlight key movements and actions.
    - Analyst → detailed metrics, explanations, and caveats.
    - Management → balanced view.

The **database design** (with `Document` linked to metrics and chunks) is already structured in a way that could support:

- A `Company` table.
- A `User` table with roles and company memberships.
- Document access filters based on user-to-company relations.

This would be the natural next step to fully meet the assignment’s “CEO sees only their company, promoter sees all” requirement.

---

## 7. Visualization Design

Visualization is **deliberately user-driven**:

- The assistant only returns `chart_data` if:
  - The user’s last message explicitly asks for visuals (keywords like “show”, “visualize”, “plot”, “graph”, “chart”, “draw”), **and**
  - A chart planner decides that a chart is meaningful.

### 7.1 LLM-driven chart planning

The planner receives:

- The user’s question.
- A small text summary of available metrics (`metrics_by_year`).

It outputs JSON with:

- `wants_chart`: boolean
- `chart_type`: "line" | "bar" | "pie" | "none"
- `metrics`: e.g. `["revenue", "net_profit"]`
- `x_axis`: usually "year"
- `aggregation`: e.g. "none" or "latest_year"

Rules encoded in the planner prompt:

- If user says “line chart / line graph” → prefer `line`.
- If user says “bar chart” → prefer `bar`.
- If user says “pie chart” or talks about “composition/share/breakdown” → prefer `pie`.
- If question doesn’t explicitly ask for any visualization → `wants_chart = false`.
- If question is about “flow chart” / “flowchart” → `chart_type = "none"`.

### 7.2 Frontend charts

`MetricsChart` uses Recharts and supports:

- Line chart – for trends over multiple years.
- Bar chart – for comparing values across years or metrics.
- Pie chart – for composition in a single year (latest available year).

Charts inherit the existing dark theme and layout; no extra page or separate visualization screen is needed.

---

## 8. Data Security & Privacy

Given the assignment’s emphasis on **public balance sheets**, the security model is scoped accordingly:

- The system is designed to work with **publicly available PDFs** such as published annual reports.
- Data is stored on the server as:
  - PDFs on the local filesystem (Render instance).
  - Structured metrics and embeddings in SQLite.

Key points:

- **No external user data** (e.g. personal PII) is handled.
- **LLM calls**:
  - Only send relevant excerpts from the user’s own uploaded PDF.
  - Do not retrieve or mix data from any other companies or documents in a given chat.
- **Document hash**:
  - Used to detect duplicate uploads and ensure consistent behaviour across identical PDFs.
- The deployment is on free-tier services; for production:
  - Replace SQLite with a managed database (Postgres).
  - Move PDFs to secure object storage (e.g. S3/GCS).
  - Add user authentication and RBAC.
  - Use HTTPS-only endpoints and appropriate secrets management.

---

## 9. Deployment

### 9.1 Backend (Render)

- Deployed as a **Python Web Service** on Render.
- Root directory: `/backend`
- Build Command:
  ```bash
  pip install -r requirements.txt
  ```
- Start Command:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
- Environment variables (example):
  - `DATABASE_URL=sqlite:///./balancesheet.db`
  - `GEMINI_API_KEY=<actual_api_key>`
  - `GEMINI_MODEL=models/gemini-2.5-flash`
  - `GEMINI_EMBEDDING_MODEL=models/text-embedding-004`

Render free tier uses an ephemeral filesystem:

- `balancesheet.db` is created automatically on startup.
- On restart/redeploy, previous PDFs and metrics may be cleared.
- For the assignment, users can re-upload PDFs as needed.

### 9.2 Frontend (Vercel)

- Deployed as a **Vite React app** on Vercel.
- Root directory: `/frontend`
- Build Command:
  ```bash
  npm run build
  ```
- Output Directory:
  ```text
  dist
  ```
- Environment variables:
  - `VITE_BACKEND_URL=https://<render-backend-url>`

The frontend uses:

```js
export const BACKEND_BASE_URL =
  import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
```

to determine where to send API calls.

### 9.3 Dockerization & future Kubernetes deployment

Both backend and frontend include Dockerfiles:

- `backend/Dockerfile`:
  - Builds a Python image with all dependencies.
  - Exposes a Uvicorn process for `app.main:app`.
- `frontend/Dockerfile`:
  - Builds the Vite app.
  - Serves `dist/` via Nginx.

This means the application is ready to be deployed in:

- Any container runtime (Docker, ECS, Cloud Run, etc.).
- Kubernetes (as a `Deployment` + `Service` + `Ingress`), with:
  - Horizontal Pod Autoscaling for the backend.
  - Managed DB (Postgres) and external object storage for PDFs.

---

## 10. Limitations & Future Work

### 10.1 Implemented but simplified

- **Roles**: CEO / Analyst / Management are used for **tone and content** of responses but not enforced via login or RBAC.
- **Single-doc chat context**: All questions in a chat are tied to one `document_id` at a time. The user can switch documents in the UI, but cross-document questions are not yet supported in a single query.

### 10.2 Not implemented (by design, as future work)

- **Real authentication / authorization**:
  - No user accounts, sessions, or tokens.
  - No per-company ACLs.
- **Persistent, scalable storage**:
  - Currently SQLite on ephemeral disk.
  - For production, would use a managed database and object storage.
- **Advanced metric coverage**:
  - Currently extracts a core set: revenue, net_profit, total_assets, total_liabilities.
  - Could be extended to:
    - EBITDA, EPS, cash flows, segment reporting, ratios, projections, etc.
- **Flowchart visualizations**:
  - Requests for “flow chart” are answered with structured text, not graphical flow diagrams.
  - Could integrate a diagram library or Mermaid.js in future.
- **Cross-document analysis**:
  - Future work: ask questions like “compare revenue growth between Company A and Company B” or “compare last three years across all uploaded entities”.

---

## 11. How to Run Locally

### 11.1 Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file in `backend` with:

```env
DATABASE_URL=sqlite:///./balancesheet.db
GEMINI_API_KEY=<your_gemini_key>
GEMINI_MODEL=models/gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=models/text-embedding-004
```

Run the server:

```bash
uvicorn app.main:app --reload
```

Visit Swagger at:  
`http://localhost:8000/docs`

### 11.2 Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env`:

```env
VITE_BACKEND_URL=http://localhost:8000
```

Run dev server:

```bash
npm run dev
```

Open:  
`http://localhost:5173`

---

## 12. Conclusion

This project delivers a **fully working prototype** of a **ChatGPT-like assistant for balance-sheet analysis**:

- It ingests **public annual report / balance-sheet PDFs**, classifies them, extracts key metrics, and builds a **RAG index** over their content.
- It allows users in different **roles** (CEO, Analyst, Management) to ask questions in natural language and receive structured, grounded answers.
- It supports **multiple documents**, quick switching between “Recent Balance Sheets”, and **on-demand visualizations** chosen by an LLM-based chart planner.
- It is **publicly deployed** using free-tier cloud services and includes **Dockerfiles** for container-based deployment.

While some advanced features (full auth/RBAC, persistent managed storage, cross-company analytics) are left as **future enhancements**, the current implementation is intentionally scoped to demonstrate:

- Strong command of **core technical concepts**:
  - LLM integration
  - RAG
  - PDF parsing
  - Web backend and frontend
- Practical **engineering trade-offs**:
  - SQLite + free-tier hosting for rapid prototyping
  - Role-aware behaviour without full auth
- Clear **architecture & deployment** story appropriate for an assignment of this scope.

