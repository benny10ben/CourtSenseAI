"""
run_pipeline.py
---------------
Automated pipeline entry point for CourtSenseAI.
Now fully session-isolated: all input/output paths are scoped
to the session directory passed in via --session-dir.
"""

import subprocess
import sys
import time
import argparse
import shutil
import os
from pathlib import Path

# ── Resolve root regardless of where the script is called from ───────────────
ROOT     = Path(__file__).resolve().parent.parent   # CourtSenseAI/
PIPELINE = ROOT / 'pipeline'


def print_header(text):
    print(f"\n{'=' * 60}\n  {text}\n{'=' * 60}")


def print_step(index, total, name):
    print(f"\n[{index}/{total}] {name}...\n{'-' * 40}")


def run_step(script_path, extra_args=None, custom_env=None):
    """Run a single pipeline script as a subprocess."""
    start = time.time()

    cmd = [sys.executable, str(script_path)]
    if extra_args:
        cmd.extend(extra_args)

    env = os.environ.copy()
    if custom_env:
        env.update(custom_env)

    result = subprocess.run(cmd, capture_output=False, env=env)

    duration = time.time() - start
    success  = result.returncode == 0
    return success, duration


def print_outputs(session_output_dir: Path):
    expected = [
        session_output_dir / 'players_pose_clean.csv',
        session_output_dir / 'rally_master.csv',
        session_output_dir / 'shots_detected.csv',
        session_output_dir / 'player_heatmap.png',
        session_output_dir / 'coaching_payload.json',
    ]
    print_header("OUTPUT SUMMARY")
    for path in expected:
        if path.exists():
            size = path.stat().st_size / 1024
            print(f"  ✅ {path.name}  ({size:.0f} KB)")
        else:
            print(f"  ❌ {path.name}  (missing)")


def main():
    parser = argparse.ArgumentParser(description="Run the CourtSenseAI Pipeline")
    parser.add_argument("--full",        action="store_true", help="Generate annotated videos")
    parser.add_argument("--coords",      type=str, default=None, help="Path to JSON coordinates file")
    parser.add_argument("--video",       type=str, default=None, help="Path to the uploaded video file")

    # ── NEW: every session gets its own isolated directory ────────────────────
    # Java passes the absolute path to ../data/sessions/{sessionId}/
    parser.add_argument("--session-dir", type=str, default=None,
                        help="Absolute path to the session's root directory")

    args = parser.parse_args()

    is_headless = args.coords is not None

    # ── Resolve session-scoped paths ─────────────────────────────────────────
    if args.session_dir:
        session_dir    = Path(args.session_dir).resolve()
        session_input  = session_dir / 'input'
        session_output = session_dir / 'output'
        session_assets = session_dir / 'assets'

        # Ensure dirs exist (Java should have created them, but be safe)
        session_input.mkdir(parents=True,  exist_ok=True)
        session_output.mkdir(parents=True, exist_ok=True)
        session_assets.mkdir(parents=True, exist_ok=True)
    else:
        # LOCAL INTERACTIVE mode — fall back to the legacy global paths
        session_dir    = ROOT
        session_input  = ROOT / 'data' / 'input'
        session_output = ROOT / 'data' / 'output'
        session_assets = ROOT / 'assets'

    # The video that all pipeline scripts operate on
    working_video = session_assets / 'badminton.mp4'

    print_header("🏸 CourtSenseAI Pipeline Starting")
    print(f"  Mode: {'HEADLESS SERVER' if is_headless else 'LOCAL INTERACTIVE'}")
    if args.session_dir:
        print(f"  Session dir: {session_dir}")

    # ── Copy the uploaded video into this session's assets/ ──────────────────
    # This replaces the old global shutil.copy2(..., ROOT/'assets'/'badminton.mp4')
    # which was the root cause of all concurrent-user corruption.
    if args.video:
        print(f"\n  📥 Copying uploaded video into session assets...")
        shutil.copy2(args.video, working_video)
        print(f"  ✅ Video ready at: {working_video}")

    # ── Build the step list ───────────────────────────────────────────────────
    steps = []

    if is_headless:
        steps.append({
            'name':   'TrackNetV3 (Ball Tracking)',
            'script': ROOT / 'TrackNetV3' / 'predict.py',
            'args': [
                '--video_file',       str(working_video),
                '--tracknet_file',    str(ROOT / 'TrackNetV3' / 'ckpts' / 'TrackNet_best.pt'),
                '--inpaintnet_file',  str(ROOT / 'TrackNetV3' / 'ckpts' / 'InpaintNet_best.pt'),
                '--save_dir',         str(session_output),   # ← session-scoped output
                '--batch_size',       '4'
            ],
            'env': {'CUDA_VISIBLE_DEVICES': ''}
        })
        steps.append({
            'name':   'Extract Pose (Headless)',
            'script': PIPELINE / 'processing' / 'extract_pose.py',
            'args':   [
                '--coords',      args.coords,
                '--video',       str(working_video),
                '--output-dir',  str(session_output),   # ← session-scoped output
            ],
            'env': None
        })
        steps.append({
            'name':   'Smooth Player IDs',
            'script': PIPELINE / 'processing' / 'smooth_ids.py',
            'args':   ['--output-dir', str(session_output)],
            'env':    None
        })
        steps.append({
            'name':   'Analyze Footprint Zones (Headless)',
            'script': PIPELINE / 'analysis' / 'footprint_zones.py',
            'args':   [
                '--coords',     args.coords,
                '--output-dir', str(session_output),
            ],
            'env': None
        })
    else:
        # Local interactive mode — prerequisites done manually
        steps.append({
            'name':   'Smooth Player IDs',
            'script': PIPELINE / 'processing' / 'smooth_ids.py',
            'args':   ['--output-dir', str(session_output)],
            'env':    None
        })

    # ── Core tail — same for both modes ──────────────────────────────────────
    core_tail = [
        {
            'name':   'Merge Ball + Player Data',
            'script': PIPELINE / 'processing' / 'merge_data.py',
            'args':   ['--output-dir', str(session_output)],
            'env':    None
        },
        {
            'name':   'Detect Shots & Rally Breaks',
            'script': PIPELINE / 'analysis' / 'detect_shots.py',
            'args':   ['--output-dir', str(session_output)],
            'env':    None
        },
        {
            'name':   'Generate Player Heatmap',
            'script': PIPELINE / 'analysis' / 'test_heatmap.py',
            'args':   ['--output-dir', str(session_output)],
            'env':    None
        },
        {
            'name':   'Build Coaching Payload',
            'script': PIPELINE / 'analysis' / 'build_coaching_payload.py',
            'args':   ['--output-dir', str(session_output)],
            'env':    None
        },
    ]
    steps.extend(core_tail)

    total   = len(steps)
    results = []

    for i, step in enumerate(steps, start=1):
        print_step(i, total, step['name'])
        success, duration = run_step(step['script'], step['args'], step['env'])

        print(f"\n  {'✅ Done' if success else '❌ Failed'}  ({duration:.1f}s)")
        results.append({'name': step['name'], 'success': success, 'duration': duration})

        if not success:
            print(f"\n  ⛔ Pipeline stopped at: {step['name']}\n")
            sys.exit(1)

    print_outputs(session_output)
    print_header("PIPELINE COMPLETE")
    for r in results:
        print(f"  {'✅' if r['success'] else '❌'} {r['name']:<40} {r['duration']:>6.1f}s")
    print(f"\n  Total time: {sum(r['duration'] for r in results):.1f}s\n")


if __name__ == '__main__':
    main()