# SkillPath AI — Adaptive Career Intelligence System

> **An Adaptive Career Intelligence System Using Large Language Models and Retrieval-Augmented Generation for Skill Validation, Personalized Learning, and Job Matching.**

SkillPath AI is an intelligent career guidance platform that helps students evaluate their technical skills, identify skill gaps, receive personalized learning roadmaps, explore suitable career paths, and discover relevant job opportunities.

---

## Architecture Overview

```
                                      +-------------------------------+
                                      |     Next.js 16 (App Router)   |
                                      |   React 19 + TypeScript + TW  |
                                      +---------------+---------------+
                                                      |
                                             REST API | Bearer Token
                                                      v
                                      +---------------+---------------+
                                      |        FastAPI Backend        |
                                      |       Python 3.11+ / Uvicorn   |
                                      +-------+-------+-------+-------+
                                              |       |       |
                 +----------------------------+       |       +-------------------------+
                 |                                    |                                 |
                 v                                    v                                 v
+-------------------------------+   +-------------------------------+   +-------------------------------+
|     Firebase Auth & Admin     |   |    Google Gemini 2.5 Flash    |   |     Qdrant Vector DB & RAG    |
|   Cloud Firestore / Fallback  |   |  Embeddings + Evaluation LLM  |   |    LangChain Chunking Pipeline|
+-------------------------------+   +-------------------------------+   +-------------------------------+
```

---

## Key Features

1. **Deterministic Skill Scoring Engine**
   - Pure Python numerical logic instead of invented LLM numbers:
     - **Skill Score** = $\frac{\text{Earned Points}}{\text{Available Points}} \times 100$
     - **Weighted Domain Score** = $\frac{\sum (\text{Weight}_i \times \text{Score}_i)}{\sum \text{Weight}_i}$
     - **Skill Gap** = $\max(0, \text{Required Level} - \text{Current Level})$
   - Unassessed skills are explicitly labeled as **Unassessed** rather than assigned fake zeros or invented numbers.

2. **Resume & Document Processing**
   - PDF & DOCX text extraction via `pdfplumber`, `pypdf`, and `python-docx`.
   - Structured candidate data extraction (Education, Claimed Skills, Projects, Experience).
   - Clear distinction between *claimed* self-reported skills and *validated* assessment scores.

3. **Hybrid Assessment Engine**
   - Standardized multiple-choice questions with deterministic verification against protected backend answer keys.
   - Rubric-governed descriptive engineering questions evaluated by Google Gemini with criteria feedback and actionable improvement suggestions.

4. **Persistent RAG Knowledge Pipeline**
   - Curated engineering documentation, rubrics, and industry requirements chunked via LangChain `RecursiveCharacterTextSplitter`.
   - 768-dimensional vector embeddings stored in persistent Qdrant with local fallback.
   - Retrieval-grounded answers with citations that state when evidence is insufficient.

5. **Personalized Learning Roadmaps**
   - Phased learning roadmaps prioritized around measured skill gaps.
   - Authentic, non-hallucinated documentation and official tutorials (MDN, React.dev, Python Docs, PostgreSQL Docs).
   - Interactive checkbox progress tracking persisted to the database.

6. **Transparent Job Matching**
   - Evaluates mandatory minimum education and years of experience independently from skill similarity.
   - Ranks administrator-managed verified job postings by required and preferred skill overlap.

7. **Administrator Governance Portal**
   - Full role-based authorization (`Student` vs `Administrator`) enforced on the backend.
   - Question bank management and rubric authoring.
   - Job creation, editing, and bulk CSV import with row-level validation and error reporting.
   - Real-time platform analytics calculated from authentic records.

---

## Project Structure

```
SkillPath/
├── .gitignore                      # Protects secrets, node_modules, and python venvs
├── render.yaml                     # Render deployment configuration for frontend & backend
├── README.md                       # Complete documentation & setup instructions
├── backend/
│   ├── Dockerfile                  # Container definition for FastAPI backend
│   ├── requirements.txt            # Python dependencies (FastAPI, Uvicorn, Pydantic, etc.)
│   ├── .env.example                # Backend environment variables template
│   ├── app/
│   │   ├── main.py                 # FastAPI application, CORS, routers
│   │   ├── core/
│   │   │   ├── config.py           # Pydantic BaseSettings
│   │   │   ├── security.py         # Firebase Admin verification + dev mock fallback
│   │   │   ├── permissions.py      # AuthenticatedUser & UserRole enum
│   │   │   └── logging.py          # Structured logger
│   │   ├── api/
│   │   │   ├── dependencies.py     # Auth dependencies (require_student, require_admin)
│   │   │   └── routes/
│   │   │       ├── health.py       # Health check endpoint
│   │   │       ├── profiles.py     # Student profile endpoints
│   │   │       ├── resumes.py      # Resume upload and analysis
│   │   │       ├── assessments.py  # Question delivery and submission evaluation
│   │   │       ├── skills.py       # Assessed scores and gap analytics
│   │   │       ├── careers.py      # Career recommendation engine
│   │   │       ├── roadmaps.py     # Adaptive roadmap generation & progress tracking
│   │   │       ├── jobs.py         # Job matching and search
│   │   │       ├── admin.py        # Admin stats, roles, jobs, bulk CSV import
│   │   │       └── rag.py          # RAG query and document ingestion
│   │   ├── schemas/                # Pydantic v2 schemas
│   │   ├── services/               # Business logic, scoring, Gemini, RAG, Qdrant
│   │   └── repositories/           # Firestore & in-memory fallback persistence
│   └── tests/
│       └── test_all.py             # Automated unit & integration test suite (11 tests)
└── frontend/
    ├── package.json                # Next.js 16, React 19, Tailwind CSS v4, Lucide
    ├── .env.example                # Frontend environment template
    ├── .env.local                  # Local dev environment
    └── src/
        ├── lib/
        │   ├── api.ts              # Typed API client
        │   └── auth-context.tsx    # Auth state & instant role switcher
        ├── components/
        │   ├── Navbar.tsx          # Responsive navigation & role switcher
        │   ├── Footer.tsx          # Platform overview footer
        │   └── AppShell.tsx        # Dashboard shell with sidebar & breadcrumbs
        └── app/
            ├── page.tsx            # Landing page
            ├── features/           # Platform overview
            ├── how-it-works/       # Interactive workflow guide
            ├── career-domains/     # Domain showcase & requirements
            ├── login/              # Sign in with instant demo buttons
            ├── register/           # Student registration
            ├── forgot-password/    # Password recovery
            ├── dashboard/          # Student analytics dashboard
            ├── profile/            # Student profile & completion bar
            ├── resume/             # PDF/DOCX resume analysis
            ├── assessment/         # Standardized test interface & scorecard
            ├── skills/             # Validated proficiencies vs unassessed skills
            ├── careers/            # Transparent career recommendations
            ├── roadmap/            # Interactive learning roadmap with progress checkboxes
            ├── jobs/               # Verified job matching & filters
            └── admin/              # Administrator portal & bulk CSV import
```

---

## Local Development Setup

### 1. Backend Setup

```bash
cd backend

# Create and activate Python virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Run automated test suite
pytest tests/test_all.py -v

# Start FastAPI development server
uvicorn app.main:app --reload --port 8000
```

The API documentation will be available at:
- Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/v1/health`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```

Open `http://localhost:3000` in your browser.

---

## Testing

Run the automated test suite verifying all 11 core sub-systems:
```bash
.\backend\venv\Scripts\python.exe -m pytest backend\tests\test_all.py -v
```

Tests include:
- `test_health_check`
- `test_skill_score_calculation` (Deterministic ratio calculation)
- `test_weighted_overall_score` (Normalized weighted calculations)
- `test_skill_gap_calculation` ($\max(0, \text{Required} - \text{Current})$)
- `test_auth_protection_on_profile`
- `test_admin_authorization_enforcement` (403 for unauthorized students)
- `test_career_recommendation_deterministic_scores`
- `test_job_matching_and_eligibility`
- `test_document_parser_validation`
- `test_assessment_questions_and_submission` (Secure answer keys)
- `test_rag_pipeline_query` (Vector retrieval and grounded generation)

---

## Deployment to Render

The repository contains a multi-service `render.yaml` blueprint:
1. Connect your GitHub repository to Render.
2. Select **New Blueprint Instance**.
3. Render automatically provisions:
   - `skillpath-backend`: FastAPI service on Python 3.11 with health check at `/api/v1/health`
   - `skillpath-frontend`: Next.js 16 service linking to backend service host
4. Configure production environment variables in Render dashboard:
   - `GEMINI_API_KEY`: Google Gemini API key
   - `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`
   - `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`
   - `QDRANT_URL`, `QDRANT_API_KEY`
