# Adaptive Traffic Signal RL — correctness revision (v2)

SUMO/TraCI traffic control on the real RESCO Cologne-1 and Cologne-3 networks.
The primary experiment is Cologne-3. Both scenarios now share one simulation and
learning implementation. This branch prepares a fresh training run; **no trained
v2 policy or improved performance claim is included**.

The original model and result files remain unchanged in `models/` and `results/`.
They were generated with the old learning/measurement logic and are incompatible
with v2. The previous README is retained as [historical material](docs/LEGACY_README.md).
See the [task checklist](docs/IMPLEMENTATION_PLAN.md) and
[validation record](docs/VALIDATION.md).

## Setup

- Python 3.10 or newer.
- Eclipse SUMO with `sumo` and `netconvert` available via `SUMO_HOME/bin` or `PATH`.
- Validation was run on Python 3.13.16 and SUMO 1.27.1 on Windows. Other versions
  should run the integration suite before training.
- Use TraCI bundled with the installed SUMO version (`SUMO_HOME/tools`), or install
  the matching `traci` package. The code has no PyTorch/Gymnasium dependency.

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
$env:RUN_SUMO_TESTS = "1"
python -m unittest discover -s tests -v
python src/validate_system.py
```

The acceptance command runs three 120-second learner checks in memory and
full-horizon simulations with baseline/untrained controllers. It writes only a
validation report under `artifacts/v2/`; it does not create a production model.
Tests use temporary directories for checkpoint lifecycle checks.

## Explicit training and resume

Start the planned 50-episode training only when ready:

```powershell
python -u src/corridor3_runner.py train --episodes 50 --duration 3600
```

Rerun that command to resume the last fully completed episode. Each episode is
followed by greedy evaluation on three fixed validation seeds. Checkpoint selection ranks mean validation trip completion rate first, then
mean queue and insertion delay. Each episode retains per-seed validation results. Exploration decays once per completed episode.

A new experiment must use a new directory; existing checkpoints are not deleted:

```powershell
python -u src/corridor3_runner.py train --output-dir artifacts/v2/cologne3-run2
```

`--reset` refuses to overwrite an existing checkpoint. The fresh-training BAT file
chooses a separate directory and prints its path. Use that same `--output-dir` for
resume, inference and comparison. A `training.lock` blocks concurrent writers.
After an OS crash, remove a stale lock only after confirming training is stopped.

The best inference model, resumable checkpoint, CSV logs and experiment manifest
are stored in `artifacts/v2/<scenario>/`, ignored by Git. Checkpoints save online,
target and best networks, replay buffer, RNG state, exploration and training
counters. Writes use atomic replacement. A partially completed episode is repeated
from the previous checkpoint after an interruption.

## Evaluation and demos

```powershell
python src/corridor3_runner.py compare --duration 3600
python src/corridor3_runner.py fixed --headless --duration 3600
python src/corridor3_runner.py dqn
python src/generate_charts.py --directory artifacts/v2/cologne3
```

Comparison requires a compatible trained model and **never starts training**.
DQN inference also fails explicitly if the model is missing or incompatible.
The default held-out test seeds are `20001..20005`; validation uses
`10001..10003`; training episode `e` uses `100 + 13*e`. Seed overlap is rejected.
Test results do not select checkpoints. All seed groups use the same route file,
so this measures variation under fixed traffic demand. Use the same duration/control settings as
training; model metadata validates these settings and hashes the network/demand.

For Cologne-1, use `--scenario cologne1` with the corridor CLI. The retained
`src/evaluate.py train|compare` and `src/demo_gui.py` entry points also use the shared
pipeline. `SumoTrafficEnv` exposes a **custom**, five-return single-intersection
API with phase features and `info['action_mask']`; it is not a `gymnasium.Env` or
an SB3 adapter.

## Control and learning contract

- Discover the active traffic-light program and all green phases from the network.
  No synthetic light IDs or two-direction assumption is used.
- A switch turns **every currently green movement yellow**, holds at least the
  original successor yellow duration (minimum 3 seconds), then holds all-red for
  1 second before enabling the requested phase. Green-to-red skips are prohibited.
  These are simulator control settings, not a municipal signal-timing certification.
- Minimum green: major 10 seconds, turn 4 seconds. Maximum green: major 45 seconds,
  turn 10 seconds. Deadlines are checked every simulation tick. Timing parameters
  must be integer multiples of SUMO's step length; unsupported settings fail early.
- Short green phases (original duration <=10 seconds) are classified as turn phases
  for these RESCO networks. A different network must validate this classification.
- Phase demand counts vehicles by their next TLS link, not all traffic in a shared
  lane. Turn demand becomes selectable at two halted vehicles or 25 seconds of
  summed waiting; hard timing constraints always take precedence.
- Per-phase features: normalized queue, vehicle count, clipped waiting, maximum
  competing normalized queue, active/target indicator, major-phase indicator and
  normalized phase clock, and remaining horizon fraction. The clock is negative during clearance. Inputs are
  **K x 8**, with variable K and no claim that every feature is bounded by 1.
- Network: `8 -> 64 ReLU -> 64 ReLU -> 1`, independently scoring each phase.
  The seventh feature exposes phase timing. The eighth gives the remaining fraction of the episode. v1 weights cannot be reused.
- Replay entries are completed at the next real decision boundary, not before
  simulation. Reward is the integral of negative halted-vehicle count, normalized
  by `8 * incoming_lane_count * 5`; clearance incurs the same cost. Rewards within
  a transition and its bootstrap use `gamma ** (elapsed_seconds / 5)`.
- The Bellman maximum uses the next legal-action mask. The training scenario ends at the declared finite horizon or natural exhaustion.
  Both end conditions stop bootstrap. The standalone environment also exposes
  an external truncation flag for its custom API.
- Fixed and actuated baselines follow sequential phases, including empty turns;
  their nominal deadlines are 42/8 and 38/8 seconds respectively, subject to the
  shared safety constraints. Max-pressure is a movement-queue/downstream-occupancy
  heuristic, not a claim of a formal stability guarantee.

## Measurements

Every simulation tick integrates queue vehicle-seconds and CO2 (mg/s × seconds).
`total_co2_kg` covers **all network lanes**, including internal lanes;
`incoming_co2_kg` covers only signal approaches. These are not comparable with the
old five-second sampled approach-only values.

Tripinfo includes unfinished and loaded-but-undeparted vehicles. Metrics distinguish
completed trips, unfinished trips, vehicles currently pending insertion and loaded
undeparted tripinfo entries. Observed waiting includes unfinished departed vehicles;
completed travel time is named separately. Empty averages are missing values, not
zero-quality scores. Validation cost includes approach queues plus pending insertion
vehicle-seconds; completion/remaining counts are always reported alongside it.
Teleporting is disabled. Collision and teleport counters are reported, and training
or validation containing either fails rather than selecting that checkpoint.

Connections have independent labels and are closed in `finally`. Different engines
can coexist; startup/close operations are serialized. Do not share one engine between
threads or reuse a tripinfo output path concurrently. Metric accumulators are bounded;
replay capacity is 20,000 transitions, and signal traces are opt-in and bounded.

## Synthetic examples

`python src/build_networks.py` writes to `nets/synthetic1/` and `nets/synthetic3/`.
It never overwrites the real Cologne benchmark networks. Synthetic scenarios need
their own trained model and experiment identity.
