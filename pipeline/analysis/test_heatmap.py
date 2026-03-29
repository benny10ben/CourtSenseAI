import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from scipy.ndimage import gaussian_filter
import argparse
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
ROOT     = Path(__file__).resolve().parents[2]

BLUR_SIGMA      = 10
GRID_SIZE       = 150
REACH_THRESHOLD = 0.30
COURT_Y_PAD     = 120
COURT_X_PAD     = 60
# ─────────────────────────────────────────────────────────────────────────────

def get_home(x_vals, y_vals):
    return x_vals.median(), y_vals.median()

def get_distance_from_home(x_vals, y_vals, home_x, home_y):
    return np.sqrt((x_vals - home_x) ** 2 + (y_vals - home_y) ** 2)

def make_density(x_vals, y_vals, x_range, y_range, grid=150, sigma=10):
    heatmap, _, _ = np.histogram2d(
        x_vals, y_vals,
        bins=grid,
        range=[x_range, y_range]
    )
    heatmap = gaussian_filter(heatmap.T, sigma=sigma)
    if heatmap.max() > 0:
        heatmap = heatmap / heatmap.max()
    return heatmap

def draw_court(ax, x_range, y_range, net_y):
    x_min, x_max = x_range
    y_min, y_max = y_range
    court_w = x_max - x_min
    court_h = y_max - y_min
    line_kw = dict(color='white', linewidth=1.2, alpha=0.85, zorder=3)

    ax.add_patch(patches.Rectangle(
        (x_min, y_min), court_w, court_h,
        linewidth=2, edgecolor='white', facecolor='none', zorder=3
    ))

    ax.axhline(y=net_y, color='yellow', linewidth=2.5, alpha=0.95, zorder=4)

    cx = (x_min + x_max) / 2
    ax.axvline(x=cx, **line_kw)

    sixth = court_h / 6
    ax.axhline(y=net_y - sixth, **line_kw)
    ax.axhline(y=net_y + sixth, **line_kw)

    inset = court_w * 0.08
    ax.axvline(x=x_min + inset, color='white', linewidth=0.8, alpha=0.45, zorder=3)
    ax.axvline(x=x_max - inset, color='white', linewidth=0.8, alpha=0.45, zorder=3)

    ax.text((x_min + x_max) / 2, net_y - 6,
            'NET', color='yellow', fontsize=8,
            ha='center', va='bottom', fontweight='bold', zorder=5)

def add_zone_labels(ax, x_range, y_range, net_y):
    cx = (x_range[0] + x_range[1]) / 2
    kw = dict(fontsize=8, color='white', alpha=0.5,
              ha='center', va='center', zorder=5, fontweight='bold')
    ax.text(cx, (y_range[0] + net_y) / 2, 'FAR\nCOURT', **kw)
    ax.text(cx, (net_y + y_range[1]) / 2, 'NEAR\nCOURT', **kw)

def plot_panel(ax, title, cmap,
               reach_x, reach_y,
               home_x, home_y,
               x_range, y_range, net_y,
               reach_radius):

    extent  = [x_range[0], x_range[1], y_range[1], y_range[0]]
    heatmap = make_density(reach_x, reach_y, x_range, y_range, GRID_SIZE, BLUR_SIGMA)

    ax.set_facecolor('#1a3320')
    ax.imshow(heatmap, extent=extent, origin='upper',
              cmap=cmap, aspect='auto', alpha=0.85,
              vmin=0, vmax=1, zorder=2)

    draw_court(ax, x_range, y_range, net_y)
    add_zone_labels(ax, x_range, y_range, net_y)

    ax.plot(home_x, home_y, 'o', color='white', markersize=12,
            markeredgecolor='black', markeredgewidth=1.5,
            zorder=7, label='Home base')

    ax.add_patch(patches.Circle(
        (home_x, home_y), radius=reach_radius,
        fill=False, edgecolor='white', linewidth=1.5,
        linestyle='--', alpha=0.6, zorder=6
    ))

    distances = np.sqrt((reach_x - home_x) ** 2 + (reach_y - home_y) ** 2)
    if len(distances) > 0:
        far_idx = distances.values.argmax()
        ax.plot(reach_x.iloc[far_idx], reach_y.iloc[far_idx],
                '*', color='yellow', markersize=14,
                markeredgecolor='black', zorder=8, label='Max reach')

    total     = max(len(reach_x), 1)
    left_pct  = 100 * (reach_x < (x_range[0] + x_range[1]) / 2).sum() / total
    net_pct   = 100 * (abs(reach_y - net_y) < (y_range[1] - y_range[0]) / 6).sum() / total
    avg_reach = distances.mean() if len(distances) > 0 else 0

    stats = (f"Reach events : {total}\n"
             f"Avg distance : {avg_reach:.0f} px\n"
             f"Left / Right : {left_pct:.0f}% / {100 - left_pct:.0f}%\n"
             f"Net zone     : {net_pct:.0f}%")
    ax.text(0.02, 0.02, stats, transform=ax.transAxes,
            fontsize=8, color='white', va='bottom', family='monospace',
            bbox=dict(facecolor='black', alpha=0.6, pad=5), zorder=9)

    ax.set_xlim(x_range)
    ax.set_ylim(y_range[1], y_range[0])
    ax.set_title(title, fontsize=12, fontweight='bold', color='white', pad=10)
    ax.set_xlabel('Court width (pixels)', fontsize=9, color='white')
    ax.set_ylabel('Court depth (pixels)', fontsize=9, color='white')
    ax.legend(loc='upper right', fontsize=8, framealpha=0.5,
              labelcolor='white', facecolor='black')
    ax.tick_params(colors='white')
    for spine in ax.spines.values():
        spine.set_edgecolor('white')

def plot_combined(ax, title,
                  p1_reach_x, p1_reach_y, p1_hx, p1_hy, p1_radius,
                  p2_reach_x, p2_reach_y, p2_hx, p2_hy, p2_radius,
                  x_range, y_range, net_y):

    extent = [x_range[0], x_range[1], y_range[1], y_range[0]]
    h1     = make_density(p1_reach_x, p1_reach_y, x_range, y_range, GRID_SIZE, BLUR_SIGMA)
    h2     = make_density(p2_reach_x, p2_reach_y, x_range, y_range, GRID_SIZE, BLUR_SIGMA)

    ax.set_facecolor('#1a3320')
    ax.imshow(h1, extent=extent, origin='upper', cmap='YlOrRd',
              aspect='auto', alpha=0.65, vmin=0, vmax=1, zorder=2)
    ax.imshow(h2, extent=extent, origin='upper', cmap='PuBuGn',
              aspect='auto', alpha=0.65, vmin=0, vmax=1, zorder=2)

    draw_court(ax, x_range, y_range, net_y)
    add_zone_labels(ax, x_range, y_range, net_y)

    ax.plot(p1_hx, p1_hy, 'o', color='#ff6666', markersize=12,
            markeredgecolor='black', markeredgewidth=1.5, zorder=7, label='P1 home')
    ax.add_patch(patches.Circle(
        (p1_hx, p1_hy), radius=p1_radius,
        fill=False, edgecolor='#ff6666', linewidth=1.5,
        linestyle='--', alpha=0.7, zorder=6
    ))

    ax.plot(p2_hx, p2_hy, 'o', color='#66ccff', markersize=12,
            markeredgecolor='black', markeredgewidth=1.5, zorder=7, label='P2 home')
    ax.add_patch(patches.Circle(
        (p2_hx, p2_hy), radius=p2_radius,
        fill=False, edgecolor='#66ccff', linewidth=1.5,
        linestyle='--', alpha=0.7, zorder=6
    ))

    d1 = np.sqrt((p1_reach_x - p1_hx) ** 2 + (p1_reach_y - p1_hy) ** 2)
    d2 = np.sqrt((p2_reach_x - p2_hx) ** 2 + (p2_reach_y - p2_hy) ** 2)
    if len(d1) > 0:
        ax.plot(p1_reach_x.iloc[d1.values.argmax()], p1_reach_y.iloc[d1.values.argmax()],
                '*', color='#ff4444', markersize=14, markeredgecolor='black',
                zorder=8, label='P1 max reach')
    if len(d2) > 0:
        ax.plot(p2_reach_x.iloc[d2.values.argmax()], p2_reach_y.iloc[d2.values.argmax()],
                '*', color='#44aaff', markersize=14, markeredgecolor='black',
                zorder=8, label='P2 max reach')

    ax.set_xlim(x_range)
    ax.set_ylim(y_range[1], y_range[0])
    ax.set_title(title, fontsize=12, fontweight='bold', color='white', pad=10)
    ax.set_xlabel('Court width (pixels)', fontsize=9, color='white')
    ax.set_ylabel('Court depth (pixels)', fontsize=9, color='white')
    ax.legend(loc='upper right', fontsize=8, framealpha=0.5,
              labelcolor='white', facecolor='black')
    ax.tick_params(colors='white')
    for spine in ax.spines.values():
        spine.set_edgecolor('white')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=str, required=True, help="Session output directory")
    args = parser.parse_args()
    
    out_dir = Path(args.output_dir)
    csv_file = out_dir / 'rally_master.csv'
    out_file = out_dir / 'player_heatmap.png'

    if not csv_file.exists():
        print(f"❌ Error: {csv_file} not found.")
        return

    df = pd.read_csv(csv_file)
    print(f"Loaded {len(df)} frames from {csv_file}")

    p1 = df[df['P1_KP16_Y'] > 0][['P1_KP16_X', 'P1_KP16_Y']].copy().reset_index(drop=True)
    p2 = df[df['P2_KP16_Y'] > 0][['P2_KP16_X', 'P2_KP16_Y']].copy().reset_index(drop=True)

    if p1.empty or p2.empty:
        print("No valid player data. Run merge_data.py first.")
        return

    print(f"P1 frames: {len(p1)}  |  P2 frames: {len(p2)}")

    p1_hx, p1_hy = get_home(p1['P1_KP16_X'], p1['P1_KP16_Y'])
    p2_hx, p2_hy = get_home(p2['P2_KP16_X'], p2['P2_KP16_Y'])
    print(f"P1 home: ({p1_hx:.0f}, {p1_hy:.0f})  |  P2 home: ({p2_hx:.0f}, {p2_hy:.0f})")

    p1_dist = get_distance_from_home(p1['P1_KP16_X'], p1['P1_KP16_Y'], p1_hx, p1_hy)
    p2_dist = get_distance_from_home(p2['P2_KP16_X'], p2['P2_KP16_Y'], p2_hx, p2_hy)

    p1_reach = p1[p1_dist >= p1_dist.quantile(REACH_THRESHOLD)].reset_index(drop=True)
    p2_reach = p2[p2_dist >= p2_dist.quantile(REACH_THRESHOLD)].reset_index(drop=True)
    print(f"P1 reach frames: {len(p1_reach)}  |  P2 reach frames: {len(p2_reach)}")

    p1_radius = p1_dist.quantile(0.70)
    p2_radius = p2_dist.quantile(0.70)

    all_x   = pd.concat([p1['P1_KP16_X'], p2['P2_KP16_X']])
    all_y   = pd.concat([p1['P1_KP16_Y'], p2['P2_KP16_Y']])
    x_range = [int(all_x.min()) - COURT_X_PAD, int(all_x.max()) + COURT_X_PAD]
    y_range = [int(all_y.min()) - COURT_Y_PAD, int(all_y.max()) + COURT_Y_PAD]

    net_y = (p1['P1_KP16_Y'].quantile(0.95) + p2['P2_KP16_Y'].quantile(0.05)) / 2

    fig, axes = plt.subplots(1, 3, figsize=(24, 11),
                             facecolor='#0d0d0d',
                             gridspec_kw={'wspace': 0.28})

    plot_panel(
        axes[0],
        title='Player 1 (Far Court) — Reach Heatmap',
        cmap='YlOrRd',
        reach_x=p1_reach['P1_KP16_X'], reach_y=p1_reach['P1_KP16_Y'],
        home_x=p1_hx, home_y=p1_hy,
        x_range=x_range, y_range=y_range,
        net_y=net_y, reach_radius=p1_radius
    )

    plot_panel(
        axes[1],
        title='Player 2 (Near Court) — Reach Heatmap',
        cmap='PuBuGn',
        reach_x=p2_reach['P2_KP16_X'], reach_y=p2_reach['P2_KP16_Y'],
        home_x=p2_hx, home_y=p2_hy,
        x_range=x_range, y_range=y_range,
        net_y=net_y, reach_radius=p2_radius
    )

    plot_combined(
        axes[2],
        title='Both Players — Combined Reach',
        p1_reach_x=p1_reach['P1_KP16_X'], p1_reach_y=p1_reach['P1_KP16_Y'],
        p1_hx=p1_hx, p1_hy=p1_hy, p1_radius=p1_radius,
        p2_reach_x=p2_reach['P2_KP16_X'], p2_reach_y=p2_reach['P2_KP16_Y'],
        p2_hx=p2_hx, p2_hy=p2_hy, p2_radius=p2_radius,
        x_range=x_range, y_range=y_range, net_y=net_y
    )

    fig.suptitle(
        'Player Reach Heatmap  —  Where they moved to hit shots\n'
        f'White/colored dot = home base  |  Dashed circle = typical reach  |  Star = max reach  |  '
        f'Top {100*(1-REACH_THRESHOLD):.0f}% farthest positions shown',
        fontsize=10, color='white', y=1.01
    )

    plt.savefig(out_file, dpi=180, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    print(f"\n✅ Heatmap saved to : {out_file}")
    print(f"   Net estimated at Y = {net_y:.0f}")
    print(f"\nTip: Adjust REACH_THRESHOLD (currently {REACH_THRESHOLD}) to change sensitivity.")
    print(f"     Adjust COURT_Y_PAD (currently {COURT_Y_PAD}) to change court height.")

if __name__ == '__main__':
    main()