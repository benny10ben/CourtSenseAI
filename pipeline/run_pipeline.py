"""
run_pipeline.py
---------------
Automated pipeline entry point for CourtSenseAI.
Runs all processing and analysis steps in order.

Prerequisites (run manually before this):
    1. python pipeline/processing/extract_pose.py    ← click court corners
    2. python pipeline/processing/smooth_ids.py      ← clean player IDs
    3. python pipeline/analysis/footprint_zones.py   ← draw zone boxes

Usage (from anywhere):
    python pipeline/run_pipeline.py           # core pipeline only
    python pipeline/run_pipeline.py --full    # also generates annotated videos + plots
"""

import subprocess
import sys
import time
from pathlib import Path

# ── Resolve root regardless of where the script is called from ───────────────
ROOT     = Path(__file__).resolve().parent.parent   # CourtSenseAI/
PIPELINE = ROOT / 'pipeline'

# ── Required input files before pipeline can start ───────────────────────────
REQUIRED_INPUTS = [
    ROOT / 'TrackNetV3' / 'output' / 'badminton_ball.csv',
    ROOT / 'data'       / 'output' / 'players_pose_full.csv',
]

# ── Expected output files after pipeline completes ───────────────────────────
EXPECTED_OUTPUTS = [
    ROOT / 'data' / 'output' / 'players_pose_clean.csv',
    ROOT / 'data' / 'output' / 'rally_master.csv',
    ROOT / 'data' / 'output' / 'shots_detected.csv',
    ROOT / 'data' / 'output' / 'rally_breaks.csv',
    ROOT / 'data' / 'output' / 'zone_footprint.csv',
    ROOT / 'data' / 'output' / 'player_heatmap.png',
    ROOT / 'data' / 'output' / 'coaching_payload.json',
]

# ── Core steps (always run) ───────────────────────────────────────────────────
CORE_STEPS = [
    {
        'name'  : 'Smooth Player IDs',
        'script': PIPELINE / 'processing' / 'smooth_ids.py',
    },
    {
        'name'  : 'Merge Ball + Player Data',
        'script': PIPELINE / 'processing' / 'merge_data.py',
    },
    {
        'name'  : 'Detect Shots & Rally Breaks',
        'script': PIPELINE / 'analysis' / 'detect_shots.py',
    },
    {
        'name'  : 'Generate Player Heatmap',
        'script': PIPELINE / 'analysis' / 'test_heatmap.py',
    },
    {
        'name'  : 'Build Coaching Payload',
        'script': PIPELINE / 'analysis' / 'build_coaching_payload.py',
    },
]

# ── Full steps (only with --full flag) ────────────────────────────────────────
FULL_STEPS = [
    {
        'name'  : 'Plot Ball Trajectory',
        'script': PIPELINE / 'output' / 'plot_trajectory.py',
    },
    {
        'name'  : 'Annotate Tracked Video',
        'script': PIPELINE / 'output' / 'annotate_video.py',
    },
    {
        'name'  : 'Verify Master Data (Full Video)',
        'script': PIPELINE / 'output' / 'verify_master.py',
    },
]

# ─────────────────────────────────────────────────────────────────────────────

def print_header(text):
    print()
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_step(index, total, name):
    print(f"\n[{index}/{total}] {name}...")
    print("-" * 40)


def check_inputs():
    """Verify all required input files exist before starting."""
    print_header("CHECKING PREREQUISITES")
    all_ok = True

    for path in REQUIRED_INPUTS:
        if path.exists():
            size = path.stat().st_size / 1024
            print(f"  ✅ {path.relative_to(ROOT)}  ({size:.0f} KB)")
        else:
            print(f"  ❌ MISSING: {path.relative_to(ROOT)}")
            all_ok = False

    if not all_ok:
        print()
        print("  ⛔ Pipeline aborted. Run the following first:")
        print("     python pipeline/processing/extract_pose.py")
        print("     python pipeline/processing/smooth_ids.py")
        print("     python pipeline/analysis/footprint_zones.py")
        print()
        sys.exit(1)

    print()
    print("  All inputs found. Starting pipeline...")


def run_step(script_path):
    """Run a single script as a subprocess. Returns (success, duration)."""
    start = time.time()

    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=False,  # stream output directly to terminal
    )

    duration = time.time() - start
    success  = result.returncode == 0
    return success, duration


def print_outputs():
    """Print a summary of all output files created."""
    print_header("OUTPUT SUMMARY")

    for path in EXPECTED_OUTPUTS:
        if path.exists():
            size = path.stat().st_size / 1024
            print(f"  ✅ {path.relative_to(ROOT)}  ({size:.0f} KB)")
        else:
            print(f"  ⚠️  Not found: {path.relative_to(ROOT)}")

    print()


def main():
    full_mode = '--full' in sys.argv

    print_header("🏸 CourtSenseAI Pipeline Starting")
    if full_mode:
        print("  Mode: FULL (includes video annotation)")
    else:
        print("  Mode: CORE  (use --full to also generate annotated videos)")

    # 1. Check all inputs exist
    check_inputs()

    # 2. Build step list
    steps   = CORE_STEPS + (FULL_STEPS if full_mode else [])
    total   = len(steps)
    results = []

    # 3. Run each step
    for i, step in enumerate(steps, start=1):
        print_step(i, total, step['name'])

        success, duration = run_step(step['script'])

        status = "✅ Done" if success else "❌ Failed"
        print(f"\n  {status}  ({duration:.1f}s)")

        results.append({
            'name'    : step['name'],
            'success' : success,
            'duration': duration,
        })

        if not success:
            print()
            print(f"  ⛔ Pipeline stopped at: {step['name']}")
            print("     Fix the error above and re-run.")
            print()
            sys.exit(1)

    # 4. Print output file summary
    print_outputs()

    # 5. Final report
    print_header("PIPELINE COMPLETE")
    total_time = sum(r['duration'] for r in results)

    for r in results:
        status = "✅" if r['success'] else "❌"
        print(f"  {status} {r['name']:<35} {r['duration']:>6.1f}s")

    print()
    print(f"  Total time: {total_time:.1f}s")
    print()


if __name__ == '__main__':
    main()