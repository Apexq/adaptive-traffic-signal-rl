"""
Generates publication-ready SVG charts from the 50-episode RESCO Cologne-3 training
and 3-mode benchmark evaluation:
  1. results/learning_curve.svg (50-Episode Waiting Time & Best Wait Progression)
  2. results/cologne3_comparison.svg (Fixed-Time vs Actuated vs 4-Phase DQN RL)
"""

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "results"


def build_learning_curve_svg():
    train_csv = RESULTS_DIR / "training_log.csv"
    rows = list(csv.DictReader(train_csv.open(encoding="utf-8")))

    w, h = 820, 430
    pad_l, pad_r, pad_t, pad_b = 80, 40, 60, 65
    plot_w = w - pad_l - pad_r
    plot_h = h - pad_t - pad_b

    max_y = 30.0
    min_y = 5.0

    def to_xy(ep_idx: int, val: float):
        x = pad_l + (ep_idx / max(1, len(rows) - 1)) * plot_w
        clamped = max(min_y, min(max_y, val))
        y = pad_t + plot_h - ((clamped - min_y) / (max_y - min_y)) * plot_h
        return x, y

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="100%">',
        f'<rect width="{w}" height="{h}" fill="#ffffff" rx="10"/>',
        '<text x="410" y="34" text-anchor="middle" font-family="Arial, sans-serif" font-size="17" font-weight="bold" fill="#0f172a">50-Episode DQN Training Convergence on Real RESCO Cologne-3 Network</text>',
        f'<line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{w - pad_r}" y2="{pad_t + plot_h}" stroke="#64748b" stroke-width="2"/>',
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + plot_h}" stroke="#64748b" stroke-width="2"/>',
        '<text x="28" y="215" text-anchor="middle" transform="rotate(-90 28 215)" font-family="Arial, sans-serif" font-size="13" font-weight="bold" fill="#334155">Average Waiting Time (seconds)</text>',
        '<text x="440" y="412" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" font-weight="bold" fill="#334155">Training Episode (1 to 50 - Each Episode = 3600s Cologne Rush Hour)</text>',
    ]

    # Horizontal grid lines
    for y_val in (10, 15, 20, 25):
        _, gy = to_xy(0, y_val)
        svg.append(f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{w - pad_r}" y2="{gy:.1f}" stroke="#e2e8f0" stroke-dasharray="4,4"/>')
        svg.append(f'<text x="{pad_l - 10}" y="{gy + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#475569">{y_val}s</text>')

    # X axis ticks
    for ep_tick in (1, 10, 20, 30, 40, 50):
        tx, _ = to_xy(ep_tick - 1, min_y)
        svg.append(f'<text x="{tx:.1f}" y="{pad_t + plot_h + 22}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#475569">Ep {ep_tick}</text>')

    # Episode wait polyline
    ep_pts = []
    best_pts = []
    for idx, r in enumerate(rows):
        wx, wy = to_xy(idx, float(r["avg_waiting_time_s"]))
        bx, by = to_xy(idx, float(r["best_wait_s"]))
        ep_pts.append(f"{wx:.1f},{wy:.1f}")
        best_pts.append(f"{bx:.1f},{by:.1f}")

    svg.append(f'<polyline fill="none" stroke="#93c5fd" stroke-width="2" points="{" ".join(ep_pts)}"/>')
    svg.append(f'<polyline fill="none" stroke="#10b981" stroke-width="3" points="{" ".join(best_pts)}"/>')

    # Legend
    svg.append('<rect x="520" y="65" width="245" height="54" fill="#f8fafc" stroke="#cbd5e1" rx="6"/>')
    svg.append('<line x1="535" y1="84" x2="565" y2="84" stroke="#93c5fd" stroke-width="2.5"/>')
    svg.append('<text x="575" y="88" font-family="Arial, sans-serif" font-size="12" fill="#334155">Episode Waiting Time (s)</text>')
    svg.append('<line x1="535" y1="105" x2="565" y2="105" stroke="#10b981" stroke-width="3"/>')
    svg.append('<text x="575" y="109" font-family="Arial, sans-serif" font-size="12" font-weight="bold" fill="#0f172a">Best Validation Record (8.67s)</text>')

    svg.append("</svg>")
    out = RESULTS_DIR / "learning_curve.svg"
    out.write_text("\n".join(svg), encoding="utf-8")
    print(f"Saved: {out}")


def build_cologne3_comparison_svg():
    summary_csv = RESULTS_DIR / "cologne3_corridor_summary.csv"
    rows = list(csv.DictReader(summary_csv.open(encoding="utf-8")))

    colors = ["#ef4444", "#f59e0b", "#10b981"]
    max_wait = 40.0

    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 420" width="100%" height="100%">',
        '<rect width="760" height="420" fill="#ffffff" rx="10"/>',
        '<text x="380" y="38" text-anchor="middle" font-family="Arial, sans-serif" font-size="17" font-weight="bold" fill="#0f172a">Real RESCO Cologne-3 Corridor (3 Intersections) - Controller Comparison</text>',
        '<line x1="95" y1="330" x2="695" y2="330" stroke="#64748b" stroke-width="2"/>',
        '<line x1="95" y1="70" x2="95" y2="330" stroke="#64748b" stroke-width="2"/>',
        '<text x="35" y="200" text-anchor="middle" transform="rotate(-90 35 200)" font-family="Arial, sans-serif" font-size="13" font-weight="bold" fill="#334155">Average Waiting Time per Vehicle (seconds)</text>',
    ]

    bar_w = 115
    spacing = 195
    start_x = 140

    for idx, r in enumerate(rows):
        x = start_x + idx * spacing
        wait = float(r["avg_waiting_time_s"])
        q = float(r["avg_corridor_queue_veh"])
        co2 = float(r["total_co2_kg"])
        bar_h = (wait / max_wait) * 240.0
        y = 330.0 - bar_h
        c = colors[idx % len(colors)]

        svg.append(f'<rect x="{x}" y="{y:.1f}" width="{bar_w}" height="{bar_h:.1f}" fill="{c}" rx="6"/>')
        svg.append(
            f'<text x="{x + bar_w/2}" y="{y - 10:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" font-weight="bold" fill="#0f172a">{wait:.2f} sn</text>'
        )
        short_label = ["1. Fixed-Time (Sabit)", "2. Actuated (Sensörlü)", "3. DQN RL (4 Fazlı Akıllı)"][idx]
        svg.append(
            f'<text x="{x + bar_w/2}" y="356" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" font-weight="bold" fill="#1e293b">{short_label}</text>'
        )
        svg.append(
            f'<text x="{x + bar_w/2}" y="376" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#475569">Kuyruk: {q:.2f} araç | CO2: {co2:.1f} kg</text>'
        )

    svg.append("</svg>")
    out = RESULTS_DIR / "cologne3_comparison.svg"
    out.write_text("\n".join(svg), encoding="utf-8")
    (RESULTS_DIR / "benchmark_comparison.svg").write_text("\n".join(svg), encoding="utf-8")
    print(f"Saved: {out}")


if __name__ == "__main__":
    build_learning_curve_svg()
    build_cologne3_comparison_svg()
