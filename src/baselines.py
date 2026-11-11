"""Controllers operating on discovered green phases and legal-action masks."""


def select_baseline(engine, tl, mode, features, mask):
    state, phases = engine.state[tl], engine.topology[tl]["phases"]
    active, elapsed = state["active"], state["elapsed"]
    legal = [i for i, ok in enumerate(mask) if ok]
    if not legal:
        raise ValueError("No legal phase")
    successor = (active + 1) % len(phases)
    if mode == "fixed":
        duration = 8 if phases[active]["turn"] else 42
        desired = successor if elapsed >= duration - 1e-9 else active
    elif mode == "actuated":
        halt = engine.movement_counts(tl)[active][0]
        duration = 8 if phases[active]["turn"] else 38
        desired = successor if halt <= 2 or elapsed >= duration - 1e-9 else active
    elif mode == "maxpressure":
        links = engine.topology[tl]["links"]
        pressures = []
        counts = engine.movement_counts(tl)
        for phase_index, phase in enumerate(phases):
            downstream = {link[1] for i in phase["links"] for link in links[i]}
            incoming = counts[phase_index][0]
            outgoing = sum(engine.conn.lane.getLastStepHaltingNumber(l) for l in downstream)
            pressures.append(incoming - outgoing)
        desired = max(legal, key=lambda i: pressures[i])
    else:
        raise ValueError(f"Unknown baseline: {mode}")
    if desired in legal:
        return desired
    if active in legal:
        return active
    return successor if successor in legal else legal[0]


class FixedTimeController:
    mode = "fixed"
    def select_action(self, obs, env):
        env.engine.baseline_mode = self.mode
        _, mask = env.engine.observe(env.tl_id, demand_mask=False)
        return select_baseline(env.engine, env.tl_id, self.mode, obs, mask)


class ActuatedController(FixedTimeController):
    mode = "actuated"


class MaxPressureController(FixedTimeController):
    mode = "maxpressure"
