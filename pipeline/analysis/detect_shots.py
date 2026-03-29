"""
detect_shots.py
---------------
Analyses the CSV to detect hits/bounces and compute shot statistics.
A hit is detected when the ball's vertical direction (Y velocity) reverses.
"""

import pandas as pd
import numpy as np
import cv2
import argparse
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
ROOT             = Path(__file__).resolve().parents[2]
MIN_SPEED        = 15.0   # px/frame — filters out tracking noise
COOLDOWN         = 10     # minimum frames between two consecutive hits
MAX_HIT_DISTANCE = 350.0  # pixels — ignore players farther than this from ball
# ─────────────────────────────────────────────────────────────────────────────

def distance(x1, y1, x2, y2):
    return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def determine_hitter(frame_num, ball_x, ball_y, master_df):
    """
    Finds which player is closest to the ball at the given frame.
    Uses wrist keypoint (KP10) if available, falls back to bounding box center.
    Returns 1, 2, or -1 if no player is close enough.
    """
    row = master_df[master_df['Frame'] == frame_num]
    if row.empty:
        return -1

    row = row.iloc[0]

    # Player 1 — use wrist if valid, else box center
    p1_wx, p1_wy = int(row['P1_KP10_X']), int(row['P1_KP10_Y'])
    if p1_wx > 0:
        d1 = distance(ball_x, ball_y, p1_wx, p1_wy)
    else:
        p1_cx = (int(row['P1_Box_X1']) + int(row['P1_Box_X2'])) // 2
        p1_cy = (int(row['P1_Box_Y1']) + int(row['P1_Box_Y2'])) // 2
        d1    = distance(ball_x, ball_y, p1_cx, p1_cy)

    # Player 2 — use wrist if valid, else box center
    p2_wx, p2_wy = int(row['P2_KP10_X']), int(row['P2_KP10_Y'])
    if p2_wx > 0:
        d2 = distance(ball_x, ball_y, p2_wx, p2_wy)
    else:
        p2_cx = (int(row['P2_Box_X1']) + int(row['P2_Box_X2'])) // 2
        p2_cy = (int(row['P2_Box_Y1']) + int(row['P2_Box_Y2'])) // 2
        d2    = distance(ball_x, ball_y, p2_cx, p2_cy)

    if min(d1, d2) > MAX_HIT_DISTANCE:
        return -1

    return 1 if d1 < d2 else 2

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=str, required=True, help="Session output directory")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    CSV_FILE        = out_dir / 'badminton_ball.csv'
    MASTER_CSV      = out_dir / 'rally_master.csv'
    OUT_SHOTS_CSV   = out_dir / 'shots_detected.csv'
    OUT_RALLIES_CSV = out_dir / 'rally_breaks.csv'

    # Safely find the video for FPS calculation
    session_video = out_dir.parent / 'assets' / 'badminton.mp4'
    VIDEO_FILE = session_video if session_video.exists() else ROOT / 'assets' / 'badminton.mp4'

    cap = cv2.VideoCapture(str(VIDEO_FILE))
    FPS = cap.get(cv2.CAP_PROP_FPS) if cap.isOpened() else 30.0
    cap.release()

    df      = pd.read_csv(CSV_FILE)
    visible = df[df['Visibility'] == 1].copy().reset_index(drop=True)

    if not MASTER_CSV.exists():
        print("⚠️  rally_master.csv not found. Player attribution skipped.")
        master_df = pd.DataFrame()
    else:
        master_df = pd.read_csv(MASTER_CSV)

    # ── Speed calculation (px/frame only) ─────────────────────────────────
    dx = visible['X'].diff()
    dy = visible['Y'].diff()
    visible['speed'] = np.sqrt(dx**2 + dy**2)

    avg_speed = visible['speed'].mean()
    max_speed = visible['speed'].max()
    max_frame = visible.loc[visible['speed'].idxmax(), 'Frame']

    print('=' * 55)
    print('SPEED STATS  (px/frame)')
    print('=' * 55)
    print(f'Average speed : {avg_speed:.1f} px/frame')
    print(f'Max speed     : {max_speed:.1f} px/frame  at frame {int(max_frame)}')
    print(f'Slow frames   : {(visible["speed"] < 5).sum()} (under 5 px/frame)')
    print(f'Fast frames   : {(visible["speed"] > 30).sum()} (over 30 px/frame)')

    # ── Shot / hit detection ───────────────────────────────────────────────
    visible['dy']      = visible['Y'].diff()
    visible['dy_sign'] = np.sign(visible['dy'])

    hits           = []
    last_hit_frame = -999

    for i in range(1, len(visible)):
        prev_sign  = visible['dy_sign'].iloc[i - 1]
        curr_sign  = visible['dy_sign'].iloc[i]
        speed      = visible['speed'].iloc[i]
        curr_frame = visible['Frame'].iloc[i]
        ball_x     = int(visible['X'].iloc[i])
        ball_y     = int(visible['Y'].iloc[i])

        if (prev_sign != curr_sign
                and curr_sign != 0
                and speed > MIN_SPEED
                and (curr_frame - last_hit_frame) > COOLDOWN):

            player_id = determine_hitter(curr_frame, ball_x, ball_y, master_df) \
                        if not master_df.empty else -1

            hits.append({
                'Frame'    : int(curr_frame),
                'X'        : ball_x,
                'Y'        : ball_y,
                'Speed'    : round(float(speed), 1),
                'Player_ID': player_id,
            })
            last_hit_frame = curr_frame

    # ── Enforce Badminton Alternation Rule ─────────────────────────────────
    if len(hits) > 0:
        seq1 = [1 if i % 2 == 0 else 2 for i in range(len(hits))]
        seq2 = [2 if i % 2 == 0 else 1 for i in range(len(hits))]
        raw_ids = [h['Player_ID'] for h in hits]
        score1  = sum(1 for r, s in zip(raw_ids, seq1) if r == s)
        score2  = sum(1 for r, s in zip(raw_ids, seq2) if r == s)
        best_seq = seq1 if score1 >= score2 else seq2
        for i, h in enumerate(hits):
            h['Player_ID'] = best_seq[i]

    print()
    print('=' * 55)
    print(f'SHOT DETECTION  ({len(hits)} hits detected)')
    print('=' * 55)
    print(f'{"Frame":>6}  {"X":>5}  {"Y":>5}  {"px/frame":>9}  {"Player":>7}')
    print('-' * 55)
    for h in hits:
        player_label = f'P{h["Player_ID"]}' if h['Player_ID'] != -1 else '?'
        print(f'{h["Frame"]:>6}  {h["X"]:>5}  {h["Y"]:>5}  {h["Speed"]:>9}  {player_label:>7}')

    p1_hits      = sum(1 for h in hits if h['Player_ID'] == 1)
    p2_hits      = sum(1 for h in hits if h['Player_ID'] == 2)
    unattributed = sum(1 for h in hits if h['Player_ID'] == -1)

    print()
    print(f'Player 1 hits : {p1_hits}')
    print(f'Player 2 hits : {p2_hits}')
    print(f'Unattributed  : {unattributed}')

    # ── Rally break detection ─────────────────────────────────────────────
    invisible_runs = []
    run_start      = None

    for _, row in df.iterrows():
        if row['Visibility'] == 0:
            if run_start is None:
                run_start = int(row['Frame'])
        else:
            if run_start is not None:
                run_len = int(row['Frame']) - run_start
                if run_len >= 50:
                    invisible_runs.append({
                        'Start_Frame': run_start,
                        'End_Frame'  : int(row['Frame']) - 1,
                        'Length'     : run_len,
                    })
                run_start = None

    print()
    print('=' * 55)
    print(f'RALLY BREAKS  ({len(invisible_runs)} gaps >= 50 invisible frames)')
    print('=' * 55)
    print(f'{"Start frame":>12}  {"End frame":>10}  {"Length":>7}')
    print('-' * 55)
    for r in invisible_runs:
        print(f'{r["Start_Frame"]:>12}  {r["End_Frame"]:>10}  {r["Length"]:>7} frames')

    print()
    print(f'Total shots detected : {len(hits)}')
    print(f'Total rally breaks   : {len(invisible_runs)}')

    pd.DataFrame(hits).to_csv(OUT_SHOTS_CSV, index=False)
    pd.DataFrame(invisible_runs).to_csv(OUT_RALLIES_CSV, index=False)

    print()
    print(f'✅ Shots saved to    : {OUT_SHOTS_CSV}')
    print(f'✅ Rallies saved to  : {OUT_RALLIES_CSV}')

if __name__ == '__main__':
    main()