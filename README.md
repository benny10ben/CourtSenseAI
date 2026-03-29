# CourtSenseAI 🏸

> **AI-powered badminton match analysis. Computer vision meets coaching intelligence.**

CourtSenseAI turns a raw match video into deep tactical insights — tracking the shuttlecock, reading player movement, detecting every hit, and generating AI coaching feedback via Gemini. Built as a production-grade, multi-tenant full-stack application combining computer vision, ML inference, a Spring Boot Java backend, and a modern Next.js frontend.

Coming in Phase 5: **CourtSenseAI Scout** — a RAG-powered intelligence layer that connects your match patterns to a knowledge base of professional badminton coaching literature, player analysis, and tactical guides. Where CourtSenseAI tells you *what happened* in your match, Scout tells you *what it means*.

---

## What It Does

Upload a badminton match video via the web dashboard. CourtSenseAI will:

- **Track the shuttlecock** frame-by-frame using TrackNetV3
- **Track both players** with YOLOv8-Pose, extracting 17 body keypoints per frame
- **Detect every shot** — speed, position, and which player hit it
- **Map court zones** — how much time each player spends in each corner
- **Generate heatmaps** — where players move to hit shots
- **Build a coaching payload** — clean JSON summarising the match
- **Generate Tactical Insights** — Uses Google Gemini to analyze the payload and provide personalized coaching feedback

And with **Scout** *(coming Phase 5)*:

- **Generate retrieval queries** automatically from your match statistics — no user input needed
- **Search a knowledge base** of professional coaching literature, BWF documents, and player tactical breakdowns using semantic search
- **Produce a structured scouting report** — specific insights grounded in retrieved expert knowledge, with every insight traceable to a source document

---

## Architecture (Multi-Tenant Session Isolated)

CourtSenseAI is designed to handle multiple concurrent users without data collision. Every browser session gets its own isolated directory for video processing.

```
Next.js Frontend (Web UI)
    │   (Uploads video + Court/Zone coordinates via Canvas)
    ▼
Spring Boot Backend (REST API)
    │   (Creates isolated session folder, saves DB row as PROCESSING)
    │   (Fires Async Background Thread — or RabbitMQ Worker in Phase 4)
    ▼
Python Pipeline (run_pipeline.py --session-dir)
    ├── TrackNetV3              → Shuttlecock tracking (ball CSV)
    ├── YOLOv8-Pose             → Player pose tracking (keypoints CSV)
    └── Analysis Scripts        → Detects shots, builds heatmaps, generates JSON
    │
    ▼
Spring Boot Backend
    │   (Reads JSON, triggers Gemini Flash API for coaching insight)
    │   (Updates DB row to COMPLETED)
    ▼
Next.js Frontend
    (Polls /status/{jobId}, renders Glassmorphism Dashboard)
```

---

## Architectural Justifications

This section explains the key decisions behind CourtSenseAI.

### 1. Polyglot Architecture — Java + Python

CourtSenseAI uses two languages, each for what it does best.

**Spring Boot handles the core logic.** Java provides type safety, clean API design, and reliable session handling. With tools like JPA and `CompletableFuture`, we can manage data and async tasks effectively while catching critical bugs early.

**Python handles ML.** Libraries like TrackNetV3, YOLOv8, OpenCV, and NumPy make Python the natural choice for computer vision. Rebuilding that in Java isn’t practical, so Python runs as a worker process — Java triggers it, passes data, and reads results.

This separation keeps things flexible. We can update ML models without touching Java, and vice versa.


### 2. Session Isolation — UUID Instead of Auth (temporary - only for now)

Instead of a full auth system, we use **UUID-based anonymous sessions**.

On first visit, the backend assigns a UUID cookie. All uploads, outputs, and DB rows are tied to that session and stored in its own folder.

This gives us:
- **No data clashes** between users  
- **Simple reset behavior** (new upload clears old session data)  
- **No auth overhead**, with an easy upgrade path later  

The trade-off is that sessions are browser-based, so clearing cookies resets everything — which is acceptable for this use case.

---

## Project Structure

```
CourtSenseAI/
│
├── frontend/                        # Next.js 15 App
│   ├── src/app/page.tsx             # Glassmorphism Dark-Mode Dashboard
│   └── src/components/Uploader.tsx  # Interactive Canvas for Court/Zone Calibration
│
├── backend/                         # Spring Boot 3 Backend
│   ├── src/main/java/com/courtsense/
│   │   ├── config/                  # WebConfig (CORS, static media), future RabbitMQ config
│   │   ├── controller/              # MatchController (upload, status, dashboard)
│   │   ├── filter/                  # SessionFilter (UUID cookie stamped on every request)
│   │   ├── model/                   # Match entity (sessionId, jobId, status, stats)
│   │   ├── repository/              # MatchRepository (session-scoped JPA queries)
│   │   └── service/                 # MatchService, FileStorageService, GeminiService
│   └── .env                         # Environment variables (Gemini API key, DB creds)
│
├── pipeline/                        # Python Processing
│   ├── processing/                  # extract_pose.py, smooth_ids.py, merge_data.py
│   ├── analysis/                    # detect_shots.py, footprint_zones.py, test_heatmap.py,
│   │                                # build_coaching_payload.py
│   └── run_pipeline.py              # Master entry point — accepts --session-dir, --coords, --video
│
├── data/
│   └── sessions/                    # 🔒 ISOLATED MULTI-TENANT DATA
│       ├── {session-uuid-1}/        # User A's private workspace
│       │   ├── input/               # Uploaded video + coords JSON (coords deleted post-run)
│       │   ├── assets/              # Session-scoped working copy of badminton.mp4
│       │   └── output/              # CSVs, player_heatmap.png → heatmap_{jobId}.png,
│       │                            # coaching_payload.json
│       └── {session-uuid-2}/        # User B's completely separate workspace
│
├── models/                          # ML model weights (YOLO)
├── TrackNetV3/                      # Third-party shuttlecock tracking model
└── scout/                           # 🔍 Phase 5 — CourtSenseAI Scout (Planned)
    ├── knowledge_base/              # Chunked, embedded coaching literature and BWF documents
    ├── retrieval/                   # Vector similarity search engine
    ├── query_engine/                # Programmatic query generation from match statistics
    └── report_builder/             # Match data + retrieved knowledge → structured scouting report
```

---

## Tech Stack

**🌐 Frontend**
- **Framework**: Next.js 15 (App Router), React
- **Styling**: Tailwind CSS, Glassmorphism design
- **Interactivity**: HTML5 Canvas — interactive court corner marking + zone drag-to-draw
- **Parsing**: React-Markdown for structured Gemini coaching output

**☕ Backend**
- **Framework**: Spring Boot 3
- **Database**: PostgreSQL (Spring Data JPA + Hibernate, schema auto-managed)
- **Session Management**: Custom `SessionFilter` — `httpOnly` UUID cookie, 30-day expiry
- **Concurrency**: `CompletableFuture.runAsync()` — non-blocking Python subprocess execution
- **AI Integration**: Google Gemini Flash API with exponential backoff retry (3 attempts: 2s → 4s → 8s)

**🐍 Python Pipeline**
- **Ball Tracking**: TrackNetV3 — deep learning shuttlecock trajectory model
- **Player Tracking**: YOLOv8-Pose (Ultralytics) — 17-keypoint pose estimation
- **Data Processing**: Pandas, NumPy, SciPy
- **Visualisation**: Matplotlib, OpenCV

**📦 Phase 4 — Planned Infrastructure**
- **Message Queue**: RabbitMQ — async job queuing with backpressure and rate limiting
- **Containerisation**: Docker + Docker Compose — reproducible multi-service deployments
- **Observability**: Prometheus (metrics scraping) + Grafana (dashboards and alerting)

**🔍 Phase 5 — Planned Intelligence**
- **RAG Engine**: Vector similarity search over an embedded coaching knowledge base
- **Query Engine**: Programmatic retrieval query generation from match statistics — no user prompt needed
- **Report Builder**: Structured scouting reports grounded in retrieved expert documents, every insight source-traceable

---

## Setup, Installation & Execution

### 1. Clone the Repository & Python Setup

Ensure you have Python 3.11+ installed.

```bash
git clone https://github.com/benny10ben/CourtSenseAI.git
cd CourtSenseAI

python -m venv venv_stable
source venv_stable/bin/activate
pip install ultralytics opencv-python pandas numpy matplotlib scipy
```

> **Note:** Download TrackNetV3 weights and place them in `TrackNetV3/ckpts/`.


### 2. PostgreSQL Setup (Linux / Fedora)

```bash
sudo dnf install postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl enable --now postgresql
sudo -i -u postgres psql
```

Run inside the psql shell:

```sql
CREATE DATABASE courtsense;
CREATE USER username WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE courtsense TO username;
\q
```


### 3. Backend Configuration & Start

Create a `.env` file in the `backend/` directory:

```env
DB_URL=jdbc:postgresql://localhost:5432/courtsense
DB_USERNAME=username
DB_PASSWORD=password
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_API_URL=https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent
INTERNAL_SECRET_KEY=badminton-pro-2026
```

Start the Spring Boot server:

```bash
cd backend
mvn clean spring-boot:run
```


### 4. Frontend Configuration & Start

Open a new terminal and start the Next.js development server:

```bash
cd frontend
npm install
npm run dev
```


### 5. Run an Analysis

1. Open your browser to `http://localhost:3000`
2. Upload a badminton `.mp4` file
3. Use the interactive canvas to click the 4 corners of the court
4. Draw the tactical quadrants for Player 1 and Player 2
5. Click **Run Pipeline** — the UI polls the backend every 3 seconds while Python processes the video inside an isolated session folder
6. Once complete, the dashboard renders the visual heatmaps, match statistics, and Gemini tactical insights

---

## Roadmap

### ✅ Phase 1 — Python Pipeline *(Complete)*

- [x] Shuttlecock tracking via TrackNetV3
- [x] Player pose extraction via YOLOv8-Pose
- [x] Player ID smoothing and interpolation
- [x] Shot detection with player attribution
- [x] Interactive court zone calibration (UI & Headless server modes)
- [x] Player reach heatmap generation
- [x] Coaching payload JSON builder

### ✅ Phase 2 — Spring Boot Backend *(Complete)*

- [x] PostgreSQL schema with auto-generation via Hibernate
- [x] Multi-tenant session isolation — UUID cookie + session-scoped filesystem
- [x] MultipartFile video upload with session cleanup on new upload
- [x] Async Python pipeline execution via `ProcessBuilder` + `CompletableFuture`
- [x] Job status polling endpoint (`/api/matches/status/{jobId}`)
- [x] Gemini Flash AI integration with exponential backoff retry
- [x] Session-scoped static media serving via Spring Boot `WebConfig`

### ✅ Phase 3 — Next.js Frontend *(Complete)*

- [x] Next.js 15 App Router setup with Tailwind CSS
- [x] Dark-Mode Glassmorphism UI
- [x] Interactive HTML5 Canvas uploader — court corner marking + zone drag-to-draw
- [x] Real-time polling engine with PROCESSING / COMPLETED / FAILED state handling
- [x] Heatmap rendering and aesthetic stat grid
- [x] React-Markdown integration for structured Gemini coaching output
- [x] `credentials: 'include'` on all fetch calls for cross-origin cookie handling


### 🔧 Phase 4 — Scaling & Reliability *(Planned)*

Right now, every upload directly starts a Python process inside a `CompletableFuture`. This works for low traffic, but doesn’t scale — multiple uploads mean multiple heavy ML jobs running at once, which can exhaust CPU/RAM and slow everything down.

Phase 4 introduces a proper infrastructure layer to fix this.

**RabbitMQ — Controlled Processing**

Instead of running ML immediately, uploads are pushed to a RabbitMQ queue. A separate Python worker processes jobs at a fixed concurrency (default: 1 at a time).

This gives us:

- **Backpressure**: uploads queue up, but only limited jobs run at once  
- **Rate limiting**: ML workload is naturally controlled via config  
- **Resilience**: failed jobs are retried automatically  
- **Scalability**: add more workers to increase throughput  

**Docker & Docker Compose**

All services (Spring Boot, Next.js, PostgreSQL, RabbitMQ, Python worker) will be containerised and managed with `docker-compose`. This removes manual setup and makes the system easy to run anywhere.

**Prometheus & Grafana — Observability**

We’ll add monitoring to track:

- **ML latency** across pipeline stages  
- **Queue depth** to detect bottlenecks  
- **Worker health** and job throughput  
- **Error rates** across the system  

**Phase 4 Checklist**

- [ ] RabbitMQ integration — Spring Boot job producer, Python worker consumer  
- [ ] Configurable worker concurrency (default: 1 concurrent ML job)  
- [ ] Dockerfile for Spring Boot backend  
- [ ] Dockerfile for Python pipeline worker  
- [ ] `docker-compose.yml` — Postgres, RabbitMQ, backend, worker, frontend  
- [ ] Micrometer + Prometheus metrics endpoint on Spring Boot  
- [ ] Grafana dashboard — ML Inference Latency, Queue Depth, Worker Health, Error Rates  
- [ ] Alerting rules for worker downtime and queue saturation  
- [ ] Proxy the video upload through a Next.js API route so `NEXT_PUBLIC_INTERNAL_SECRET` never reaches the browser bundle — move the secret to a server-side env var only


### 🔍 Phase 5 — CourtSenseAI Scout *(Planned)*

Scout is a RAG-powered intelligence layer built on top of CourtSenseAI. It reads `coaching_payload.json` and automatically generates retrieval queries from match statistics — no user input required. Those queries search a knowledge base of professional coaching literature, BWF technical documents, and player tactical breakdowns using vector similarity search. The result is a structured scouting report where every insight is grounded in retrieved expert knowledge and traceable to a source document.

CourtSenseAI tells you *what happened* in your match. Scout tells you *what it means*.

- [ ] Knowledge base construction — scraping, chunking, embedding, and indexing coaching documents
- [ ] Query engine — programmatic query generation from match statistics (no user prompt needed)
- [ ] Semantic retrieval — vector similarity search over the embedded knowledge base
- [ ] Structured report generation — match data + retrieved knowledge → scouting report
- [ ] Spring Boot integration — new `/api/scout` endpoints added to the existing backend
- [ ] Sources panel in frontend — every Scout insight linked to the expert document behind it

---

## Acknowledgements

- [TrackNetV3](https://github.com/alenzenx/TrackNetV3) — shuttlecock tracking model
- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) — pose estimation
- [ByteTrack](https://github.com/ifzhang/ByteTrack) — multi-object tracking