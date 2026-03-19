"""
build_coaching_payload.py
--------------------------
Reads all pipeline output CSVs and builds a single clean JSON payload
for Gemini AI coaching insights.

Reads:
  - data/output/shots_detected.csv
  - data/output/rally_breaks.csv
  - data/output/zone_footprint.csv
  - data/output/rally_master.csv
  - assets/badminton.mp4              ← for accurate duration

Produces:
  - data/output/coaching_payload.json

Usage:
    python3 build_coaching_payload.py
"""

import cv2
import json
import pandas as pd
import numpy as np
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
ROOT          = Path(__file__).resolve().parents[2]
SHOTS_CSV     = ROOT / 'data'   / 'output' / 'shots_detected.csv'
RALLIES_CSV   = ROOT / 'data'   / 'output' / 'rally_breaks.csv'
FOOTPRINT_CSV = ROOT / 'data'   / 'output' / 'zone_footprint.csv'
MASTER_CSV    = ROOT / 'data'   / 'output' / 'rally_master.csv'
VIDEO_FILE    = ROOT / 'assets' / 'badminton.mp4'
OUT_JSON      = ROOT / 'data'   / 'output' / 'coaching_payload.json'
# ─────────────────────────────────────────────────────────────────────────────


def load_and_check(path, required_cols=None):
    if not path.exists():
        raise FileNotFoundError(
            f"❌ Required file missing: {path}\n   Run the full pipeline first."
        )
    if path.stat().st_size == 0:
        print(f"  ⚠️  {path.name} is empty — returning empty DataFrame.")
        return pd.DataFrame(columns=required_cols) if required_cols else pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        print(f"  ⚠️  {path.name} has no data rows — returning empty DataFrame.")
        return pd.DataFrame(columns=required_cols) if required_cols else pd.DataFrame()


def get_video_duration(video_path):
    """Read actual frame count and FPS directly from the video file."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"  ⚠️  Cannot open video. Falling back to CSV frame count.")
        return None, None
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps          = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    return total_frames, fps


def build_hit_stats(shots_df, player_id):
    """Compute hit count and relative speed stats for a given player."""
    player_shots = shots_df[shots_df['Player_ID'] == player_id]

    if player_shots.empty:
        return {
            'count'         : 0,
            'avg_speed_pxpf': 0.0,
            'max_speed_pxpf': 0.0,
            'min_speed_pxpf': 0.0,
        }

    return {
        'count'         : len(player_shots),
        'avg_speed_pxpf': round(float(player_shots['Speed'].mean()), 1),
        'max_speed_pxpf': round(float(player_shots['Speed'].max()), 1),
        'min_speed_pxpf': round(float(player_shots['Speed'].min()), 1),
    }


def build_speed_comparison(shots_df):
    """
    Compare relative hitting power between players.
    Speed ratio > 1.0 means P1 hits harder than P2.
    km/h excluded — requires court pixel calibration for accuracy.
    """
    p1     = shots_df[shots_df['Player_ID'] == 1]['Speed']
    p2     = shots_df[shots_df['Player_ID'] == 2]['Speed']
    p1_avg = float(p1.mean()) if not p1.empty else 0.0
    p2_avg = float(p2.mean()) if not p2.empty else 0.0
    ratio  = round(p1_avg / p2_avg, 2) if p2_avg > 0 else 0.0

    harder_hitter = ('player_1' if p1_avg > p2_avg
                     else 'player_2' if p2_avg > p1_avg
                     else 'equal')

    return {
        'harder_hitter'       : harder_hitter,
        'p1_avg_speed_pxpf'   : round(p1_avg, 1),
        'p2_avg_speed_pxpf'   : round(p2_avg, 1),
        'speed_ratio_p1_vs_p2': ratio,
    }


def build_zone_stats(footprint_df, player_id):
    """Compute zone percentage breakdown for a given player."""
    player_zones = footprint_df[footprint_df['Player'] == player_id]

    if player_zones.empty:
        return {
            'front_left_pct'    : 0.0,
            'front_right_pct'   : 0.0,
            'back_left_pct'     : 0.0,
            'back_right_pct'    : 0.0,
            'most_occupied_zone': 'unknown',
        }

    total    = player_zones['Frame_Count'].sum()
    if total == 0:
        total = 1

    zone_map = dict(zip(player_zones['Zone'], player_zones['Frame_Count']))
    fl       = zone_map.get('Front-Left',  0)
    fr       = zone_map.get('Front-Right', 0)
    bl       = zone_map.get('Back-Left',   0)
    br       = zone_map.get('Back-Right',  0)

    most_occupied = max(zone_map, key=zone_map.get) if zone_map else 'unknown'

    return {
        'front_left_pct'    : round((fl / total) * 100, 1),
        'front_right_pct'   : round((fr / total) * 100, 1),
        'back_left_pct'     : round((bl / total) * 100, 1),
        'back_right_pct'    : round((br / total) * 100, 1),
        'most_occupied_zone': most_occupied,
    }


def build_home_position(footprint_df, player_id):
    """
    Derives where the player naturally stands using zone percentages.
    More accurate than pixel math since zone data is already validated.

    Horizontal: left% (FL+BL) vs right% (FR+BR)
    Depth:      front% (FL+FR) vs back% (BL+BR) within their own half
    """
    player_zones = footprint_df[footprint_df['Player'] == player_id]
    if player_zones.empty:
        return 'unknown'

    zone_map = dict(zip(player_zones['Zone'], player_zones['Frame_Count']))
    total    = sum(zone_map.values())
    if total == 0:
        return 'unknown'

    fl = zone_map.get('Front-Left',  0)
    fr = zone_map.get('Front-Right', 0)
    bl = zone_map.get('Back-Left',   0)
    br = zone_map.get('Back-Right',  0)

    left_pct  = (fl + bl) / total * 100
    right_pct = (fr + br) / total * 100
    front_pct = (fl + fr) / total * 100
    back_pct  = (bl + br) / total * 100

    # Horizontal bias
    if left_pct > 60:
        h_pos = 'left side'
    elif right_pct > 60:
        h_pos = 'right side'
    else:
        h_pos = 'center'

    # Depth within own half
    if front_pct > 60:
        depth = 'front-court'
    elif back_pct > 60:
        depth = 'back-court'
    else:
        depth = 'mid-court'

    return f"{h_pos}, {depth}"


def build_court_coverage(master_df, player_id, all_players_data):
    """
    Converts pixel range into a readable description of how much
    of the court the player covered during the match.
    """
    x_col = f'P{player_id}_KP16_X'
    y_col = f'P{player_id}_KP16_Y'

    valid = master_df[(master_df[x_col] > 0) & (master_df[y_col] > 0)]
    if valid.empty:
        return {'horizontal': 'unknown', 'vertical': 'unknown'}

    x_range = int(valid[x_col].max() - valid[x_col].min())
    y_range = int(valid[y_col].max() - valid[y_col].min())

    # Reference: total court pixel width and depth from all players combined
    all_x       = all_players_data['all_x']
    all_y       = all_players_data['all_y']
    court_w     = int(all_x.max() - all_x.min())
    court_h     = int(all_y.max() - all_y.min())

    h_pct = (x_range / court_w * 100) if court_w > 0 else 0
    v_pct = (y_range / court_h * 100) if court_h > 0 else 0

    # Convert percentage to readable label
    def label(pct):
        if pct >= 70:   return 'wide'
        elif pct >= 40: return 'moderate'
        else:           return 'narrow'

    return {
        'horizontal': f"{label(h_pct)} ({h_pct:.0f}% of court width)",
        'vertical'  : f"{label(v_pct)} ({v_pct:.0f}% of court depth)",
    }


def build_rally_stats(rallies_df, fps, total_frames):
    """Compute rally count and duration stats."""
    if rallies_df.empty:
        duration_sec = round(total_frames / fps, 1)
        return {
            'total_rallies'            : 1,
            'avg_rally_length_seconds' : duration_sec,
            'longest_rally_seconds'    : duration_sec,
            'shortest_rally_seconds'   : duration_sec,
        }

    lengths_sec = rallies_df['Length'] / fps
    return {
        'total_rallies'            : len(rallies_df) + 1,
        'avg_rally_length_seconds' : round(float(lengths_sec.mean()), 1),
        'longest_rally_seconds'    : round(float(lengths_sec.max()), 1),
        'shortest_rally_seconds'   : round(float(lengths_sec.min()), 1),
    }


def main():
    print("=" * 55)
    print("🏸 Building Coaching Payload")
    print("=" * 55)

    # ── Load all CSVs ─────────────────────────────────────────────────────
    print("\nLoading pipeline outputs...")
    shots_df     = load_and_check(SHOTS_CSV)
    rallies_df   = load_and_check(
        RALLIES_CSV,
        required_cols=['Start_Frame', 'End_Frame', 'Length']
    )
    footprint_df = load_and_check(FOOTPRINT_CSV)
    master_df    = load_and_check(MASTER_CSV)

    # ── Get accurate duration from video ──────────────────────────────────
    video_frames, fps = get_video_duration(VIDEO_FILE)
    if video_frames and fps:
        duration_sec = round(video_frames / fps, 1)
        print(f"  Video frames  : {video_frames}  ({fps:.2f} fps)")
    else:
        fps          = 30.0
        video_frames = len(master_df)
        duration_sec = round(video_frames / fps, 1)
        print(f"  CSV frames    : {video_frames}  (fallback)")

    total_shots  = len(shots_df[shots_df['Player_ID'] != -1])
    unattributed = len(shots_df[shots_df['Player_ID'] == -1])
    print(f"  Duration      : {duration_sec}s")
    print(f"  Shots         : {total_shots} attributed, {unattributed} unattributed")

    # ── Shared court reference data for relative position calculations ────
    all_players_data = {
        'all_x': pd.concat([
            master_df[master_df['P1_KP16_X'] > 0]['P1_KP16_X'],
            master_df[master_df['P2_KP16_X'] > 0]['P2_KP16_X'],
        ]),
        'all_y': pd.concat([
            master_df[master_df['P1_KP16_Y'] > 0]['P1_KP16_Y'],
            master_df[master_df['P2_KP16_Y'] > 0]['P2_KP16_Y'],
        ]),
    }

    # ── Build payload ─────────────────────────────────────────────────────
    payload = {
        "match_summary": {
            "duration_seconds": duration_sec,
            "total_shots"     : total_shots,
            **build_rally_stats(rallies_df, fps, video_frames),
        },
        "speed_comparison": build_speed_comparison(shots_df),
        "player_1": {
            "court_side"   : "far",
            "hits"         : build_hit_stats(shots_df, 1),
            "zones"        : build_zone_stats(footprint_df, 1),
            "home_position": build_home_position(footprint_df, 1),
            "coverage"     : build_court_coverage(master_df, 1, all_players_data),
        },
        "player_2": {
            "court_side"   : "near",
            "hits"         : build_hit_stats(shots_df, 2),
            "zones"        : build_zone_stats(footprint_df, 2),
            "home_position": build_home_position(footprint_df, 2),
            "coverage"     : build_court_coverage(master_df, 2, all_players_data),
        },
    }

    # ── Save JSON ─────────────────────────────────────────────────────────
    with open(OUT_JSON, 'w') as f:
        json.dump(payload, f, indent=2)

    # ── Print summary ─────────────────────────────────────────────────────
    print()
    print("=" * 55)
    print("📦 PAYLOAD SUMMARY")
    print("=" * 55)
    print(json.dumps(payload, indent=2))
    print()
    print(f"✅ Saved to: {OUT_JSON}")


if __name__ == '__main__':
    main()