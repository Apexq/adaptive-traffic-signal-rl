"""Exports real SUMO Cologne-3 road geometry, signal states, and vehicle trajectories
for Fixed-Time vs DQN RL side-by-side HTML5 Canvas playback on the showcase website.
"""
import csv
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR / "src"))

from env import TrafficSimulation
from corridor3_runner import RealNetworkSimulation, SUMOCFG_C3

WEB_DATA_DIR = BASE_DIR / "web" / "data"
NET_XML = BASE_DIR / "nets" / "cologne3" / "cologne3.net.xml"

# Bounding box framing the 3 intersections cleanly
X_MIN, X_MAX = 10460.0, 11260.0
Y_MIN, Y_MAX = 12870.0, 13440.0


def to_norm(x: float, y: float) -> tuple[float, float]:
    nx = (x - X_MIN) / (X_MAX - X_MIN)
    # Invert Y for HTML5 Canvas (0 at top)
    ny = 1.0 - (y - Y_MIN) / (Y_MAX - Y_MIN)
    return round(nx * 1000.0, 1), round(ny * 700.0, 1)


def extract_road_geometry() -> list[dict]:
    tree = ET.parse(NET_XML)
    root = tree.getroot()
    lanes = []
    for edge in root.findall("edge"):
        eid = edge.get("id", "")
        if eid.startswith(":") or edge.get("function") == "internal":
            continue
        for lane in edge.findall("lane"):
            allow = lane.get("allow", "")
            disallow = lane.get("disallow", "")
            # Filter out pedestrian-only or rail lanes
            if allow == "pedestrian" or "passenger" in disallow and "all" in disallow:
                continue
            shape_str = lane.get("shape", "")
            if not shape_str:
                continue
            pts = []
            in_bounds = False
            for pair in shape_str.split():
                px, py = map(float, pair.split(","))
                if X_MIN - 150 <= px <= X_MAX + 150 and Y_MIN - 150 <= py <= Y_MAX + 150:
                    in_bounds = True
                pts.append(to_norm(px, py))
            if in_bounds and len(pts) >= 2:
                lanes.append({
                    "id": lane.get("id"),
                    "pts": pts,
                    "w": float(lane.get("width", 3.2)),
                })
    return lanes


def record_mode(mode: str, duration: int = 180, seed: int = 20001) -> dict:
    model_path = BASE_DIR / "models" / "dqn_cologne3_trained.json" if mode == "dqn" else None
    sim = RealNetworkSimulation(
        SUMOCFG_C3, mode=mode, use_gui=False, seed=seed, sim_duration=duration, model_path=model_path
    )
    frames = []
    stop_points = []

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        trip_path = Path(tmp) / "trips.xml"
        try:
            sim.engine.reset(tripinfo_path=trip_path)
            conn = sim.engine.conn

            # Discover controlled stop line positions once
            for tl in sim.engine.tl_ids:
                links = sim.engine.topology[tl]["links"]
                for idx, link_group in enumerate(links):
                    if link_group:
                        in_lane = link_group[0][0]
                        shape = conn.lane.getShape(in_lane)
                        if shape:
                            sx, sy = shape[-1]
                            nx, ny = to_norm(sx, sy)
                            stop_points.append({"tl": tl, "link": idx, "x": nx, "y": ny})

            step = 0
            while not (sim.engine.terminated or sim.engine.truncated):
                for tl in sim.engine.tl_ids:
                    if not sim.engine.ready(tl):
                        continue
                    features, mask = sim.engine.observe(tl)
                    if mode == "dqn":
                        action = sim.agent.select_action(features, mask, evaluate=True)
                    else:
                        from baselines import select_baseline
                        state = sim.engine.state[tl]
                        lower, upper = sim.engine.bounds(tl)
                        b_mask = [True] * len(features)
                        if state["elapsed"] < lower - 1e-9:
                            b_mask = [i == state["active"] for i in range(len(features))]
                        elif state["elapsed"] >= upper - 1e-9:
                            b_mask[state["active"]] = False
                        action = select_baseline(sim.engine, tl, mode, features, b_mask)
                    sim.engine.apply(tl, action, demand_mask=(mode == "dqn"))

                sim.engine.tick()
                step += 1

                # Record every 1 second
                tl_states = {}
                for tl in sim.engine.tl_ids:
                    tl_states[tl] = conn.trafficlight.getRedYellowGreenState(tl)

                lights_frame = []
                for sp in stop_points:
                    sig_str = tl_states.get(sp["tl"], "")
                    ch = sig_str[sp["link"]] if sp["link"] < len(sig_str) else "r"
                    c = "g" if ch in ("g", "G") else ("y" if ch in ("y", "Y") else "r")
                    lights_frame.append(c)

                vehs = []
                halting_in_view = 0
                for vid in conn.vehicle.getIDList():
                    vx, vy = conn.vehicle.getPosition(vid)
                    if X_MIN <= vx <= X_MAX and Y_MIN <= vy <= Y_MAX:
                        nx, ny = to_norm(vx, vy)
                        angle = round(conn.vehicle.getAngle(vid), 1)
                        spd = round(conn.vehicle.getSpeed(vid), 1)
                        if spd < 0.2:
                            halting_in_view += 1
                        vehs.append([nx, ny, angle, 1 if spd < 0.2 else 0])

                frames.append({
                    "t": step,
                    "q": sum(sim.engine.last_queues.values()),
                    "qh": halting_in_view,
                    "co2": round(sim.engine.metrics()["total_co2_kg"], 2),
                    "arrived": sim.engine.metrics()["completed_trips"],
                    "l": "".join(lights_frame),
                    "v": vehs,
                })

            final_metrics = sim.engine.metrics()
        finally:
            sim.engine.close()

    return {
        "mode": mode,
        "stop_points": [{"x": s["x"], "y": s["y"]} for s in stop_points],
        "frames": frames,
        "summary": {
            "queue_vehicle_seconds": final_metrics["queue_vehicle_seconds"],
            "completed_trips": final_metrics["completed_trips"],
            "total_co2_kg": round(final_metrics["total_co2_kg"], 2),
            "avg_queue": round(final_metrics["avg_corridor_queue_veh"], 2),
        },
    }


def export_benchmark_json():
    summary_csv = BASE_DIR / "results" / "cologne3_corridor_summary.csv"
    if not summary_csv.exists():
        summary_csv = BASE_DIR / "artifacts" / "v2" / "cologne3" / "benchmark_summary.csv"

    rows = []
    if summary_csv.exists():
        with summary_csv.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append({
                    "mode": r["mode"],
                    "wait_mean": round(float(r["observed_avg_waiting_time_s_mean"]), 2),
                    "wait_std": round(float(r["observed_avg_waiting_time_s_std"]), 2),
                    "queue_mean": round(float(r["avg_corridor_queue_veh_mean"]), 2),
                    "queue_std": round(float(r["avg_corridor_queue_veh_std"]), 2),
                    "travel_mean": round(float(r["completed_avg_travel_time_s_mean"]), 2),
                    "co2_mean": round(float(r["total_co2_kg_mean"]), 2),
                    "completed_mean": round(float(r["completed_trips_mean"]), 1),
                    "collisions_mean": round(float(r["collisions_mean"]), 2),
                    "teleports_mean": round(float(r["teleports_mean"]), 2),
                })

    # Load 50-episode learning curve from legacy training log for historical convergence section
    train_log = BASE_DIR / "results" / "training_log.csv"
    learning_curve = []
    if train_log.exists():
        with train_log.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                learning_curve.append({
                    "ep": int(r["episode"]),
                    "wait": round(float(r["avg_waiting_time_s"]), 2),
                    "best": round(float(r["best_wait_s"]), 2),
                    "queue": round(float(r["avg_corridor_queue_veh"]), 2),
                })

    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = WEB_DATA_DIR / "benchmark_data.json"
    out.write_text(json.dumps({"benchmark": rows, "learning_curve": learning_curve}, indent=2), encoding="utf-8")
    print(f"Saved benchmark JSON: {out}")


def main():
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    export_benchmark_json()
    print("Extracting Cologne-3 road geometry...")
    lanes = extract_road_geometry()
    print(f"Extracted {len(lanes)} road lanes.")

    print("Recording Fixed-Time (180s, seed=20001)...")
    fixed_rec = record_mode("fixed", duration=180, seed=20001)

    print("Recording DQN RL (180s, seed=20001)...")
    dqn_rec = record_mode("dqn", duration=180, seed=20001)

    payload = {
        "meta": {"width": 1000, "height": 700, "duration": 180, "seed": 20001},
        "lanes": lanes,
        "stop_points": dqn_rec["stop_points"],
        "fixed": fixed_rec["frames"],
        "dqn": dqn_rec["frames"],
    }
    out_file = WEB_DATA_DIR / "playback_cologne3.json"
    out_file.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"Saved playback JSON ({out_file.stat().st_size / 1024:.1f} KB): {out_file}")


if __name__ == "__main__":
    main()
