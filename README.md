# Adaptive Traffic Signal RL

SUMO/TraCI adaptive traffic signal control on the real **RESCO Cologne-1** and **Cologne-3** arterial networks using a topology-agnostic **Phase-Competing Deep Q-Network (`8 -> 64 ReLU -> 64 ReLU -> 1`)**.

🌐 **Live Interactive Showcase & SUMO Playback:** [https://apexq.github.io/adaptive-traffic-signal-rl/](https://apexq.github.io/adaptive-traffic-signal-rl/)

The primary benchmark environment is the 3-intersection **Cologne-3** corridor. Both Cologne-1 and Cologne-3 share one unified simulation, safety, and learning pipeline with **no PyTorch or Gymnasium runtime dependency**. Original v1 baseline artifacts remain preserved under `models/` and `results/` as well as in Git (`backup-main-v1-50eps` and `v1-50eps-legacy`).

## Cologne-3 Benchmark Results (5 Held-Out Seeds: `20001..20005`, `1800s`)

Trained policy: `models/dqn_cologne3_trained.json`

| Control Mode | Avg Wait (s) | Avg Corridor Queue (veh) | Avg Travel Time (s) | Total CO₂ (kg) | Completed Trips | Safety (Collisions / Teleports) |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| **1. Fixed-Time** | 32.69 ± 2.07 | 18.05 ± 0.28 | 83.28 | 279.75 | 1610.0 | 0 / 0 |
| **2. Actuated** | 37.04 ± 2.82 | 15.73 ± 0.40 | 91.73 | 304.93 | 1600.6 | 0 / 0 |
| **3. Max-Pressure** | 12.66 ± 1.04 | 5.67 ± 0.22 | 62.21 | 225.06 | 1624.6 | 2 collisions / 1 teleport across 5 seeds |
| **4. DQN RL (Trained)** | **13.44 ± 0.82** | **6.02 ± 0.21** | **63.25** | **227.91** | **1626.4** | **0 / 0 (100% clean)** |

- **-58.9%** lower average waiting time compared to Fixed-Time (`32.69s` → `13.44s`).
- **-63.7%** lower average waiting time compared to classic Actuated control (`37.04s` → `13.44s`).
- Highest completed trip throughput (`1626.4`) with **zero collisions, zero emergency-braking teleports**, while rule-based Max-Pressure triggered collisions and a teleport on seed `20003`.

## Setup

- Python 3.10 or newer (verified on Python 3.13/3.14 on Windows).
- Eclipse SUMO with `sumo` and `netconvert` available via `SUMO_HOME/bin` or `PATH`.
- Use TraCI bundled with the installed SUMO version (`SUMO_HOME/tools`), or install `requirements.txt`.

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
$env:RUN_SUMO_TESTS = "1"
python -m unittest discover -s tests -v
python src/validate_system.py
```

The `validate_system.py` acceptance command runs three 120-second learner checks in memory and full-horizon simulations with baseline/untrained controllers. It writes only a validation report under `artifacts/v2/` and does not overwrite production models.

## Quick Launchers (`bat/`) & Interactive Web Showcase (`web/`)

Windows `.bat` launchers live under `bat/`:

| Script | Purpose |
| --- | --- |
| `bat/1_Sabit_Sureli_Fixed_Izle.bat` | Open SUMO GUI running `Fixed-Time` on Cologne-3 |
| `bat/2_Sensorlu_Actuated_Izle.bat` | Open SUMO GUI running `Actuated` on Cologne-3 |
| `bat/3_Max_Pressure_Izle.bat` | Open SUMO GUI running `Max-Pressure` on Cologne-3 |
| `bat/4_Akilli_DQN_RL_Izle.bat` | Open SUMO GUI running trained `DQN RL` on Cologne-3 |
| `bat/5_Tum_Modlari_Karsilastir_Tablo.bat` | Run all 4 modes across 5 seeds and print comparison table |
| `bat/6_Sistem_Testlerini_Calistir.bat` | Run unit tests and SUMO integration suite |

To preview the static web showcase locally over HTTP (required for browser `fetch()`):

```powershell
# Double-click web/siteyi_baslat.bat, or run:
python -m http.server 8080 --directory web
```

To re-export the 1800-second SUMO playback JSON and benchmark JSON under `web/data/`:

```powershell
python web/scripts/export_playback.py --duration 1800
```

## Explicit Training and Resume

Run explicit 50-episode training from CLI when needed:

```powershell
python -u src/corridor3_runner.py train --episodes 50 --duration 3600
```

Rerun that command to resume from the last completed episode. Each episode is followed by greedy evaluation on three fixed validation seeds (`10001..10003`). Checkpoint selection ranks mean validation trip completion rate first, then mean queue and insertion delay. Exploration decays once per completed episode.

To start an isolated new experiment without overwriting existing checkpoints, pass a fresh `--output-dir`:

```powershell
python -u src/corridor3_runner.py train --output-dir artifacts/v2/cologne3-run2
```

`--reset` refuses to overwrite an existing checkpoint. A `training.lock` file blocks concurrent writers. Best inference models, resumable checkpoints, CSV logs, and manifests are stored under `artifacts/v2/<scenario>/` (ignored by Git) using atomic replacement.

## Evaluation and CLI Demos

```powershell
python src/corridor3_runner.py compare --duration 1800
python src/corridor3_runner.py fixed --headless --duration 3600
python src/corridor3_runner.py dqn
python src/generate_charts.py --directory artifacts/v2/cologne3
```

Comparison requires a compatible trained model and **never starts training**. DQN inference also fails explicitly if the model is missing or incompatible. Held-out test seeds are `20001..20005`; validation uses `10001..10003`; training episode `e` uses `100 + 13*e` (seed overlap is rejected). Model metadata validates duration/control settings and hashes the network and demand routes.

For Cologne-1, pass `--scenario cologne1` to `src/corridor3_runner.py`. The retained `src/evaluate.py train|compare` and `src/demo_gui.py` entry points also use the shared pipeline. `SumoTrafficEnv` exposes a custom five-return single-intersection API with phase features and `info['action_mask']` (not a `gymnasium.Env` adapter).

## Control and Learning Contract

- Discovers the active traffic-light program and all green phases dynamically from the SUMO network (no synthetic IDs or fixed two-direction assumptions).
- Every phase switch transitions **all currently green movements to yellow** (holding at least the successor yellow duration, minimum `3s`), followed by `1s` all-red clearance before activating the target phase. Direct green-to-red skips are prohibited.
- Enforced bounds per tick: major phases `10s..45s`, turn phases `4s..10s` (short green phases `<= 10s` in RESCO networks are classified as turn phases).
- Phase demand counts vehicles by their next TLS link rather than shared-lane totals. Turn phases become selectable at `>= 2` halted vehicles or `>= 25s` accumulated waiting (hard timing constraints always take precedence).
- Each candidate phase produces an 8-dimensional feature vector (`K x 8` input, variable `K`): normalized queue, vehicle count, clipped waiting, maximum competing normalized queue, active-phase indicator, major-phase indicator, normalized phase clock (negative during clearance), and remaining horizon fraction.
- Policy network (`8 -> 64 ReLU -> 64 ReLU -> 1`) scores each phase independently.
- Replay transitions complete at the next real decision boundary (`elapsed_seconds`), accumulating negative halted-vehicle reward normalized by `8 * incoming_lane_count * 5` across clearance and green intervals with duration-aware discounting (`gamma ** (elapsed_seconds / 5)`).
- Bellman targets use the masked legal-action maximum and terminate bootstrapping on both horizon end and natural traffic exhaustion.

## Measurements

Every simulation tick integrates queue vehicle-seconds and CO₂ (`mg/s * seconds`). `total_co2_kg` covers **all network lanes** (including internal lanes); `incoming_co2_kg` covers only signal approaches.

Tripinfo accounts for completed trips, unfinished departed vehicles, pending insertions, and loaded-but-undeparted entries. Observed waiting time includes unfinished departed vehicles; completed travel time is reported separately. Teleporting is disabled, and collision/teleport counts are explicitly tracked—any training or validation episode containing a collision or teleport is rejected from checkpoint selection.

## Synthetic Examples

`python src/build_networks.py` writes synthetic 1-intersection and 3-intersection networks to `nets/synthetic1/` and `nets/synthetic3/` without touching the real Cologne benchmark networks. Synthetic scenarios require their own trained models and experiment identities.
