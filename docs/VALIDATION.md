# Validation record

Python 3.13.16 and Eclipse SUMO 1.27.1 on Windows.

- 20 regression tests passed with RUN_SUMO_TESTS=1.
- Three 120-second Cologne-3 learner checks each recorded 72 transitions and 41
  optimizer updates. Each recorded three horizon truncations with final observations.
- Five 3600-second simulation checks passed: Cologne-3 fixed, actuated,
  max-pressure and untrained DQN, plus Cologne-1 fixed. The checks found zero
  collisions, teleports or direct green-to-red transitions.
- The emissions and queue accumulators matched independent per-step TraCI reads.
- Checkpoint reload reproduced the next sampled update and exploration decision.
  An injected replacement failure preserved the previous checkpoint.
- These checks cover the training pipeline and simulator. Policy quality will be
  evaluated after training on the held-out seeds.

Run the regression suite with `python -m unittest discover -s tests -v` and
the acceptance checks with `python src/validate_system.py`.
