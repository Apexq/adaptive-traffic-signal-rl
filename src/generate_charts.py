"""Charts for v2 CSVs; no fixed result labels or clipped axes."""
import argparse
import csv
from html import escape
from pathlib import Path


def chart(rows, x_key, y_key, output, title):
    values = [(str(r[x_key]), float(r[y_key])) for r in rows if r.get(y_key) not in (None, "")]
    if not values:
        raise ValueError(f"No numeric {y_key} values to plot")
    maximum = max(1.0, max(y for _, y in values) * 1.1)
    width = max(760, len(values) * 14)
    points = " ".join(f"{70 + i * (width - 100) / max(1, len(values)-1):.1f},{330-y/maximum*260:.1f}" for i, (_, y) in enumerate(values))
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 400">',
           '<rect width="100%" height="100%" fill="white"/>',
           f'<text x="40" y="30" font-family="Arial" font-size="18">{escape(title)}</text>',
           '<path d="M70 60 V330 H730" stroke="#64748b" fill="none"/>',
           f'<text x="10" y="70">{maximum:.1f}</text>',
           '<text x="40" y="330">0</text>',
           f'<polyline points="{points}" fill="none" stroke="#059669" stroke-width="2"/>']
    stride = max(1, len(values)//8)
    for i, (label, y) in enumerate(values):
        if i % stride == 0 or i == len(values)-1:
            x = 70 + i * (width-100)/max(1, len(values)-1)
            svg.append(f'<text x="{x:.1f}" y="355" text-anchor="middle" font-size="11">{escape(label)}</text>')
    svg.append('</svg>')
    Path(output).write_text('\n'.join(svg), encoding="utf-8")


def build_learning_curve_svg(directory):
    with (directory / "training_log.csv").open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    chart(rows, "episode", "validation_cost", directory / "learning_curve.svg",
          "Validation queue + insertion delay (vehicle seconds)")


def build_cologne3_comparison_svg(directory):
    with (directory / "benchmark_summary.csv").open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    chart(rows, "mode", "selection_cost_mean", directory / "benchmark_comparison.svg",
          "Held-out benchmark mean queue + insertion delay (vehicle seconds)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent.parent / "artifacts/v2/cologne3")
    args = parser.parse_args()
    if (args.directory / "training_log.csv").exists():
        build_learning_curve_svg(args.directory)
    if (args.directory / "benchmark_summary.csv").exists():
        build_cologne3_comparison_svg(args.directory)
