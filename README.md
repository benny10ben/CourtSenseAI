# CourtSenseAI 🏸

> **AI-powered badminton match analysis. Computer vision meets coaching intelligence.**

CourtSenseAI turns a raw match video into deep tactical insights — tracking the shuttlecock, reading player movement, detecting every hit, and ultimately generating AI coaching feedback via Gemini. Built as a full-stack learning project combining computer vision, ML inference, data engineering, and Spring Boot.

---

## What It Does

Upload a badminton match video. CourtSenseAI will:

- **Track the shuttlecock** frame-by-frame using TrackNetV3
- **Track both players** with YOLOv8-Pose, extracting 17 body keypoints per frame
- **Detect every shot** — speed, position, and which player hit it
- **Map court zones** — how much time each player spends in each corner
- **Generate heatmaps** — where players move to hit shots
- **Build a coaching payload** — clean JSON summarising the match, ready for Gemini AI

---

## Architecture

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
    Spring Boot Backend         → REST API, user management, Gemini integration
            │
            ▼
    Frontend                    → Match dashboard, coaching insights UI
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
│   │   └── build_coaching_payload.py # Build coaching_payload.json for Gemini
│   ├── output/
│   │   ├── annotate_video.py        # Draw ball trail on original video
│   │   ├── plot_trajectory.py       # 2D shuttlecock trajectory plot
│   │   └── verify_master.py         # QA — draw skeleton + ball on video
│   └── run_pipeline.py              # Single automated entry point
│
├── backend/                         # Spring Boot (in progress)
│   └── src/
│
├── data/
│   ├── input/                       # Uploaded videos (future)
│   ├── output/                      # All pipeline outputs
│   └── temp/
│
├── models/                          # ML model weights
├── assets/                          # Source videos
├── TrackNetV3/                      # Third-party ball tracking repo
└── .env
```

---

## Pipeline Flow

### Step 1 — Ball Tracking
Run TrackNetV3 to track the shuttlecock. This produces `badminton_ball.csv` with frame-by-frame X, Y, visibility.

```bash
CUDA_VISIBLE_DEVICES="" python TrackNetV3/predict.py \
  --video_file assets/badminton.mp4 \
  --tracknet_file TrackNetV3/ckpts/TrackNet_best.pt \
  --inpaintnet_file TrackNetV3/ckpts/InpaintNet_best.pt \
  --save_dir TrackNetV3/output \
  --batch_size 4
```

### Step 2 — Player Pose Extraction *(interactive)*
Opens a window. Click 4 court corners to define the court boundary. YOLOv8-Pose then tracks both players through every frame.

```bash
python pipeline/processing/extract_pose.py
```

### Step 3 — Smooth Player IDs
YOLO sometimes swaps player IDs. This corrects them, assigns P1 = far court, P2 = near court, and interpolates any missing frames.

```bash
python pipeline/processing/smooth_ids.py
```

### Step 4 — Court Zone Drawing *(interactive)*
Opens a window. Draw 4 zone boxes for each player (Front-Left, Front-Right, Back-Left, Back-Right). Automatically analyses how much time each player spent in each zone.

```bash
python pipeline/analysis/footprint_zones.py
```

### Step 5 — Run Automated Pipeline
Everything else runs automatically in the correct order.

```bash
# Core analysis only
python pipeline/run_pipeline.py

# Core + annotated videos + trajectory plots
python pipeline/run_pipeline.py --full
```

The automated pipeline runs:
1. `smooth_ids.py` → clean player IDs
2. `merge_data.py` → fuse all data into `rally_master.csv`
3. `detect_shots.py` → detect hits, attribute to players
4. `test_heatmap.py` → generate reach heatmaps
5. `build_coaching_payload.py` → produce `coaching_payload.json`

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
| `coaching_payload.json` | Clean match summary JSON — the only file sent to Gemini |

---

## Coaching Payload

The final output of the pipeline is a compact JSON sent to Gemini for coaching analysis:

```json
{
  "match_summary": {
    "duration_seconds": 21.0,
    "total_shots": 22,
    "total_rallies": 1,
    "avg_rally_length_seconds": 21.0
  },
  "speed_comparison": {
    "harder_hitter": "player_1",
    "speed_ratio_p1_vs_p2": 2.38
  },
  "player_1": {
    "court_side": "far",
    "hits": { "count": 11, "avg_speed_pxpf": 69.6 },
    "zones": { "back_right_pct": 38.0, "most_occupied_zone": "Back-Right" },
    "home_position": "right side, mid-court",
    "coverage": { "horizontal": "wide (97%)", "vertical": "narrow (35%)" }
  },
  "player_2": { ... }
}
```

Gemini Flash receives this alongside a coaching prompt and returns specific tactical insights for each player.

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
| Authentication | Spring Security + JWT |
| Database ORM | Spring Data JPA + Hibernate |
| Database | PostgreSQL |
| Async job processing | Spring @Async + ExecutorService |
| AI Integration | Google Gemini Flash API |

**🌐 Frontend** *(Phase 3)*

| Purpose | Library / Tool |
| --- | --- |
| UI Framework | - |
| Styling | - |
| Charts & Heatmaps | - |

**🛠️ Dev Tools**

| Purpose | Tool |
| --- | --- |
| IDE | Visual Studio Code |
| API Testing | Postman |
| Version Control | Git + GitHub |
| Build Tool | Maven |

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
- [ ] Project setup and database schema
- [ ] Video upload endpoint
- [ ] Async pipeline job trigger and status tracking
- [ ] REST API for match results and stats
- [ ] Gemini Flash integration — coaching insights per match
- [ ] User authentication via Spring Security
- [ ] Match history per user

### 📋 Phase 3 — Frontend
- [ ] Match upload and processing status page
- [ ] Match dashboard — stats, heatmaps, shot log
- [ ] Coaching insights panel — Gemini AI feedback
- [ ] Player comparison view
- [ ] Historical match comparison

### 💡 Phase 4 — Future Improvements
- [ ] Multi-match trend analysis across sessions
- [ ] Doubles match support (4 players)
- [ ] Accurate speed calibration using court reference points
- [ ] Shot type classification (smash, drop, clear, drive)
- [ ] Overhead detection using wrist-shoulder relationship

---

## Setup

### Prerequisites
- Python 3.11+
- Java 21+
- Maven 3.9+
- PostgreSQL (for Phase 2)

### Python Environment

```bash
python -m venv venv_stable
source venv_stable/bin/activate
pip install ultralytics opencv-python pandas numpy matplotlib scipy
```

### Model Weights
Download and place in `models/`:
- `yolo26n-pose.pt` — auto-downloads on first run via Ultralytics
- `TrackNet_best.pt` and `InpaintNet_best.pt` — see TrackNetV3 repo for download instructions, place in `TrackNetV3/ckpts/`

### Environment Variables
Create a `.env` file at the project root:

```
GEMINI_API_KEY=your_key_here
DB_URL=jdbc:postgresql://localhost:5432/courtsense
DB_USERNAME=your_db_user
DB_PASSWORD=your_db_password
```

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

## Acknowledgements

- [TrackNetV3](https://github.com/alenzenx/TrackNetV3) — shuttlecock tracking model
- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) — pose estimation
- [ByteTrack](https://github.com/ifzhang/ByteTrack) — multi-object tracking

---