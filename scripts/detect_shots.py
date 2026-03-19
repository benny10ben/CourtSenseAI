"""
detect_shots.py
---------------
Analyses the CSV to detect hits/bounces and compute shot statistics.
A hit is detected when the ball's vertical direction (Y velocity) reverses.

Usage:
    python3 detect_shots.py
"""

import pandas as pd
import numpy as np

# ── Config ────────────────────────────────────────────────────────────────────
CSV_FILE = 'TrackNetV3/output/badminton_ball.csv'
MIN_SPEED = 16.0   # was 3.0 — filters out tracking noise
COOLDOWN  = 10     # minimum frames between two consecutive hits
FPS             = 30.0  # set to your video's actual FPS for speed in km/h
PIXELS_PER_METER = 50.0 # rough estimate — tune based on your court size in pixels
# ─────────────────────────────────────────────────────────────────────────────

def px_per_frame_to_kmh(speed_px_per_frame):
    meters_per_frame = speed_px_per_frame / PIXELS_PER_METER
    meters_per_second = meters_per_frame * FPS
    return meters_per_second * 3.6


def main():
    df = pd.read_csv(CSV_FILE)
    visible = df[df['Visibility'] == 1].copy().reset_index(drop=True)

    # ── Speed calculation ──────────────────────────────────────────────────
    dx = visible['X'].diff()
    dy = visible['Y'].diff()
    visible['speed'] = np.sqrt(dx**2 + dy**2)

    avg_speed = visible['speed'].mean()
    max_speed = visible['speed'].max()
    max_frame = visible.loc[visible['speed'].idxmax(), 'Frame']

    print('=' * 50)
    print('SPEED STATS')
    print('=' * 50)
    print(f'Average speed : {avg_speed:.1f} px/frame  (~{px_per_frame_to_kmh(avg_speed):.0f} km/h)')
    print(f'Max speed     : {max_speed:.1f} px/frame  (~{px_per_frame_to_kmh(max_speed):.0f} km/h)  at frame {int(max_frame)}')
    print(f'Slow frames   : {(visible["speed"] < 5).sum()} (under 5 px/frame)')
    print(f'Fast frames   : {(visible["speed"] > 30).sum()} (over 30 px/frame)')

    # ── Shot / hit detection ───────────────────────────────────────────────
    # Detect Y direction reversal (ball changes from going down to going up or vice versa)
    visible['dy'] = visible['Y'].diff()
    visible['dy_sign'] = np.sign(visible['dy'])

    hits = []
    last_hit_frame = -999
    for i in range(1, len(visible)):
        prev_sign = visible['dy_sign'].iloc[i - 1]
        curr_sign = visible['dy_sign'].iloc[i]
        speed     = visible['speed'].iloc[i]
        curr_frame = visible['Frame'].iloc[i]

        if (prev_sign != curr_sign
                and curr_sign != 0
                and speed > MIN_SPEED
                and (curr_frame - last_hit_frame) > COOLDOWN):
            hits.append({
                'Frame'    : int(curr_frame),
                'X'        : int(visible['X'].iloc[i]),
                'Y'        : int(visible['Y'].iloc[i]),
                'Speed'    : round(float(speed), 1),
                'Speed_kmh': round(px_per_frame_to_kmh(speed), 0),
            })
            last_hit_frame = curr_frame

    print()
    print('=' * 50)
    print(f'SHOT DETECTION  ({len(hits)} hits detected)')
    print('=' * 50)
    print(f'{"Frame":>6}  {"X":>5}  {"Y":>5}  {"px/frame":>9}  {"~km/h":>6}')
    print('-' * 50)
    for h in hits:
        print(f'{h["Frame"]:>6}  {h["X"]:>5}  {h["Y"]:>5}  {h["Speed"]:>9}  {h["Speed_kmh"]:>6.0f}')

    # ── Rally detection ───────────────────────────────────────────────────
    # A rally break = 3+ consecutive invisible frames
    invisible_runs = []
    run_start = None
    for _, row in df.iterrows():
        if row['Visibility'] == 0:
            if run_start is None:
                run_start = int(row['Frame'])
        else:
            if run_start is not None:
                run_len = int(row['Frame']) - run_start
                if run_len >= 50:
                    invisible_runs.append((run_start, int(row['Frame']) - 1, run_len))
                run_start = None

    print()
    print('=' * 50)
    print(f'RALLY BREAKS  ({len(invisible_runs)} gaps of 3+ invisible frames)')
    print('=' * 50)
    print(f'{"Start frame":>12}  {"End frame":>10}  {"Length":>7}')
    print('-' * 50)
    for start, end, length in invisible_runs:
        print(f'{start:>12}  {end:>10}  {length:>7} frames')

    print()
    print(f'Total shots detected : {len(hits)}')
    print(f'Total rally breaks   : {len(invisible_runs)}')


if __name__ == '__main__':
    main()
