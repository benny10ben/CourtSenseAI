# CourtSenseAI 🏸

> **AI-powered badminton match analysis. Computer vision meets coaching intelligence.**

CourtSenseAI turns a raw match video into deep tactical insights — tracking the shuttlecock, reading player movement, detecting every hit, and generating AI coaching feedback via Gemini. Built as a full-stack learning project combining computer vision, ML inference, data engineering, and Spring Boot.

Coming in Phase 4: **CourtSenseAI Scout** — a RAG-powered intelligence layer that connects your match patterns to a knowledge base of professional badminton coaching literature, player analysis, and tactical guides. Where CourtSenseAI tells you *what happened* in your match, Scout tells you *what it means*.

---

## What It Does

Upload a badminton match video. CourtSenseAI will:

- **Track the shuttlecock** frame-by-frame using TrackNetV3
- **Track both players** with YOLOv8-Pose, extracting 17 body keypoints per frame
- **Detect every shot** — speed, position, and which player hit it
- **Map court zones** — how much time each player spends in each corner
- **Generate heatmaps** — where players move to hit shots
- **Build a coaching payload** — clean JSON summarising the match, ready for AI analysis

And with **Scout** *(coming Phase 4)*:

- **Generate retrieval queries** automatically from your match statistics — no user input needed
- **Search a knowledge base** of professional coaching literature, BWF documents, and player tactical breakdowns using semantic search
- **Produce a structured scouting report** — specific insights grounded in retrieved expert knowledge, with every insight traceable to a source document

---

## Architecture

### CourtSenseAI

```
Video Input
    │
    ├── TrackNetV3              → Shuttlecock tracking (ball CSV)
    └── YOLOv8-Pose             → Player pose tracking (keypoints CSV)
            │
            ▼
    Python Pipeline             → Processing, analysis, JSON output
            │
            ▼
    Spring Boot Backend         → REST API, database, Gemini integration
            │
            ▼
        Frontend                → Match dashboard, coaching insights UI
```

### CourtSenseAI Scout *(Phase 4)*

```
coaching_payload.json
        │
        ▼
Scout Query Builder
(converts match stats into retrieval queries)
        │
        ▼
Vector Knowledge Base
(semantic search over indexed coaching documents)
        │
        ▼
Retrieved Chunks
(top relevant passages per query)
        │
        ▼
LLM Synthesis
(combines chunks + match data into structured report)
        │
        ▼
Structured Scouting Report
(served via Spring Boot API to frontend)
```

---

## Project Structure

```
CourtSenseAI/
│
├── pipeline/                        # All Python processing
│   ├── processing/
│   │   ├── extract_pose.py          # YOLOv8 player tracking (interactive)
│   │   ├── smooth_ids.py            # Fix player ID swaps, interpolate gaps
│   │   └── merge_data.py            # Fuse ball + player → rally_master.csv
│   ├── analysis/
│   │   ├── detect_shots.py          # Hit detection + player attribution
│   │   ├── footprint_zones.py       # Court zone drawing + time analysis (interactive)
│   │   ├── test_heatmap.py          # Player reach heatmap generation
│   │   └── build_coaching_payload.py
│   ├── output/
│   │   ├── annotate_video.py        # Draw ball trail on original video
│   │   ├── plot_trajectory.py       # 2D shuttlecock trajectory plot
│   │   └── verify_master.py         # QA — draw skeleton + ball on video
│   ├── scout/                       # Scout knowledge base pipeline (Phase 4)
│   │   └── ...                      # Scrape → chunk → embed → store
│   └── run_pipeline.py              # Single automated entry point
│
├── backend/                         # Spring Boot backend
│   ├── src/
│   ├── pom.xml
│   └── .env                         # Hidden environment variables (not committed)
│
├── data/
│   ├── input/                       # Uploaded videos (future)
│   ├── output/                      # All pipeline outputs
│   ├── scout/                       # Scout knowledge base data (Phase 4)
│   │   └── raw/                     # Scraped coaching documents
│   └── temp/
│
├── models/                          # ML model weights
├── assets/                          # Source videos
└── TrackNetV3/                      # Third-party ball tracking repo
```

---

## Outputs

All outputs land in `data/output/`. Nothing is committed to git.

**📊 Data Files**

| File | Description |
| --- | --- |
| `rally_master.csv` | Master dataset — every frame with ball position + both players' full 17-keypoint pose |
| `shots_detected.csv` | Every detected hit — frame, position, speed (px/frame), player attribution |
| `rally_breaks.csv` | Detected gaps between rallies (50+ invisible frames) |
| `court_zones.csv` | Zone box coordinates saved from interactive calibration |
| `zone_footprint.csv` | Per-zone frame counts per player |

**🖼️ Visuals**

| File | Description |
| --- | --- |
| `player_heatmap.png` | 3-panel reach heatmap — P1, P2, and combined overlay on court |
| `trajectory.png` | Full shuttlecock path coloured by frame number (purple → yellow) |

**🎬 Videos** — generated with the `--full` flag

| File | Description |
| --- | --- |
| `badminton_tracked.mp4` | Original video with red ball dot and yellow trail overlay |
| `master_verification.mp4` | Original video with full skeleton, bounding boxes, and ball — used for QA |

**🤖 AI Input**

| File | Description |
| --- | --- |
| `coaching_payload.json` | Clean match summary JSON — the input to Gemini and to Scout |

---

## Tech Stack

**🐍 Python Pipeline**

| Purpose | Library / Tool |
| --- | --- |
| Shuttlecock tracking | TrackNetV3 |
| Player pose estimation | YOLOv8-Pose (Ultralytics) |
| Multi-object tracking | ByteTrack |
| Data processing | Pandas, NumPy |
| Computer vision | OpenCV |
| Visualisation | Matplotlib, SciPy |

**☕ Backend** *(Phase 2)*

| Purpose | Library / Tool |
| --- | --- |
| REST API | Spring Boot 3 |
| Database ORM | Spring Data JPA + Hibernate |
| Database | PostgreSQL |
| HTTPS Client | Spring WebFlux (WebClient) |
| AI Integration | Google Gemini Flash API |

**🌐 Frontend** *(Phase 3)*

| Purpose | Library / Tool |
| --- | --- |
| TBD | React / Next.js / Android (Kotlin) |

**🔍 Scout — RAG Intelligence Layer** *(Phase 4 — will be built soon)*

| Purpose | Library / Tool |
| --- | --- |
| Knowledge base & retrieval | Will be built soon |
| Embedding model | Will be built soon |
| Vector database | Will be built soon |
| Query engine | Will be built soon |
| Report synthesis | Will be built soon |

**🛠️ Dev Tools**

| Purpose | Tool |
| --- | --- |
| IDE | Visual Studio Code |
| API Testing | - |
| Version Control | Git + GitHub |
| Build Tool | Maven |

---

## Setup, Installation & Execution

Follow these steps to set up the full stack on your local machine and run your first match analysis.

### 1. Clone the Repository

```bash
git clone https://github.com/benny10ben/CourtSenseAI.git
cd CourtSenseAI
```

### 2. Python Environment Setup

Ensure you have Python 3.11+ installed.

```bash
python -m venv venv_stable
source venv_stable/bin/activate
pip install ultralytics opencv-python pandas numpy matplotlib scipy
```

> Download TrackNetV3 weights and place them in `TrackNetV3/ckpts/`. The `yolo26n-pose.pt` model will auto-download on first run.

### 3. PostgreSQL Setup (Linux / Fedora)

The Spring Boot backend requires a PostgreSQL database to store match data and AI insights.

**Install and initialize:**

```bash
sudo dnf install postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl enable --now postgresql
```

**Create the database and user:**

```bash
sudo -i -u postgres psql
```

Run inside the psql shell:

```sql
CREATE DATABASE courtsense;
CREATE USER username WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE courtsense TO courtsense_admin;
\q
```

> You do not need to manually create tables. Spring Boot Hibernate auto-generates the schema on startup.

### 4. Backend Configuration

Navigate to the `backend/` directory and create a `.env` file:

```bash
cd backend
touch .env
```

Add the following — this file is gitignored and never committed:

```
DB_URL=jdbc:postgresql://localhost:5432/courtsense
DB_USERNAME=username
DB_PASSWORD=password

GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_API_URL=https://generativelanguage.googleapis.com/...

INTERNAL_SECRET_KEY=your_custom_secret_password_here
```

Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com/).

### 5. Start the Spring Boot Backend

Ensure you have Java 21+ and Maven installed. From the `backend/` directory:

```bash
mvn clean spring-boot:run
```

The server starts on `http://localhost:8080`.

### 6. Run the Python Data Pipeline

Open a new terminal, activate `venv_stable`, and run from the project root in order.

**Step 6a — Ball Tracking**

```bash
CUDA_VISIBLE_DEVICES="" python TrackNetV3/predict.py \
  --video_file assets/badminton.mp4 \
  --tracknet_file TrackNetV3/ckpts/TrackNet_best.pt \
  --inpaintnet_file TrackNetV3/ckpts/InpaintNet_best.pt \
  --save_dir TrackNetV3/output \
  --batch_size 4
```

**Step 6b — Player Pose Extraction** *(interactive — click 4 court corners)*

```bash
python pipeline/processing/extract_pose.py
```

**Step 6c — Smooth Player IDs**

```bash
python pipeline/processing/smooth_ids.py
```

**Step 6d — Court Zone Drawing** *(interactive — draw 4 zones per player)*

```bash
python pipeline/analysis/footprint_zones.py
```

**Step 6e — Run Automated Analysis**

```bash
# Core analysis only
python pipeline/run_pipeline.py

# Core + annotated QA videos + trajectory plots
python pipeline/run_pipeline.py --full
```

### 7. Trigger the AI Coaching API

With `coaching_payload.json` generated and Spring Boot running:

```bash
curl -X POST http://localhost:8080/api/matches/process-latest \
     -H "X-Internal-Secret: your_custom_secret_password_here"
```

The backend parses the Python output, requests tactical advice from Gemini, and saves the full match report to PostgreSQL.

---

## Notes on Speed Data

Shot speed is stored in `px/frame` — a relative unit. Absolute km/h conversion requires knowing the court's pixel-to-meter ratio for your specific camera angle and position. Until calibrated, speed values are only meaningful as relative comparisons between players (e.g. Player 1 hits 2.38x harder than Player 2).

---

## Development Environment

Built and tested on the following machine:

| Component | Details |
| --- | --- |
| OS | Fedora Linux 43 (Workstation Edition) |
| Machine | HP Laptop 15s-du3xxx |
| Processor | 11th Gen Intel® Core™ i5-1135G7 × 8 |
| Memory | 16.0 GiB RAM |
| IDE | Visual Studio Code |

> All pipeline scripts run on CPU. No GPU required — TrackNetV3 runs with `CUDA_VISIBLE_DEVICES=""` and YOLOv8 uses `device='cpu'`. Expect ~2–5 minutes processing time per minute of video on this hardware.

---

## Roadmap

### ✅ Phase 1 — Python Pipeline
- [x] Shuttlecock tracking via TrackNetV3
- [x] Player pose extraction via YOLOv8-Pose
- [x] Player ID smoothing and interpolation
- [x] Shot detection with player attribution
- [x] Interactive court zone calibration
- [x] Player reach heatmap generation
- [x] Coaching payload JSON builder
- [x] Automated pipeline runner

### 🔄 Phase 2 — Spring Boot Backend *(in progress)*
- [x] Project setup and database schema
- [x] Data parsing from Python output
- [x] Security gatekeeper and endpoint protection
- [x] Gemini Flash AI integration
- [ ] Video upload endpoint
- [ ] Async pipeline job trigger
- [ ] User authentication via Spring Security
- [ ] Match history per user

### 📋 Phase 3 — Frontend
- [ ] Match upload and processing status page
- [ ] Match dashboard — stats, heatmaps, shot log
- [ ] Coaching insights panel — Gemini AI feedback
- [ ] Player comparison view

### 🔍 Phase 4 — CourtSenseAI Scout *(coming soon)*
Scout is a RAG-powered intelligence layer built on top of CourtSenseAI. It reads `coaching_payload.json` and automatically generates retrieval queries from your match statistics — no user input needed. Those queries search a knowledge base of professional coaching literature, BWF technical documents, and player tactical breakdowns. The result is a structured scouting report where every insight is grounded in and traceable to a specific expert source.

- [ ] Knowledge base construction — scraping, chunking, embedding, and indexing coaching documents
- [ ] Query engine — programmatic query generation from match statistics
- [ ] Semantic retrieval — vector similarity search over the knowledge base
- [ ] Structured report generation — match data + retrieved knowledge → scouting report
- [ ] Spring Boot integration — new Scout endpoints added to existing backend
- [ ] Sources panel in frontend — every insight linked to the expert document behind it

---

## Acknowledgements

- [TrackNetV3](https://github.com/alenzenx/TrackNetV3) — shuttlecock tracking model
- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) — pose estimation
- [ByteTrack](https://github.com/ifzhang/ByteTrack) — multi-object tracking

---