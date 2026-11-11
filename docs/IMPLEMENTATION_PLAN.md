# Implementation tasks

Scope: prepare and verify the corrected system. Full training and final trained-model
benchmark remain a separate, explicitly started stage.

- [x] T1: Preserve legacy artifacts; isolate v2 outputs; fingerprint scenario and control settings;
  prevent the synthetic builder from overwriting benchmark inputs.
- [x] T2: Share topology discovery across Cologne-1/3; movement-specific counts; yellow/all-red
  state machine; hard per-tick green deadlines.
- [x] T3: Real replay transitions, integrated negative cost, masked Bellman targets,
  elapsed-time discounting, terminal/truncation handling and observation validation.
- [x] T4: Independent TraCI connections, exception cleanup, atomic writes, exact learner
  resume (replay/RNG), schema validation and one-writer training lock.
- [x] T5: Exact per-step emissions/queue integration, unfinished vehicle reporting,
  safe empty metrics, validation-based checkpoint selection and disjoint seed sets.
- [x] T6a: Unit and real-SUMO regression checks; three short learner smoke episodes;
  full-horizon control acceptance checks. No production model saved.
- [ ] T6b: Once training is authorized, review the first 3–5 full learning episodes
  before allowing the entire 50-episode run to proceed. Short smoke checks cannot
  establish learning convergence.
- [ ] T7: Fresh 50-episode training, validation checkpoints and convergence review.
- [ ] T8: Held-out multi-seed comparison of the trained model and baselines.

The single-intersection compatibility work is included in this revision. The shared
MLP retains two 64-unit hidden layers; the input expands from 6 to 7 to expose phase
clock state. v1 models are intentionally rejected; all original files are preserved.
