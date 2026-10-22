"""Deterministic delay propagation and constrained tail-swap search.

Times are minutes from midnight in one synthetic local operating day.
"""
from dataclasses import dataclass, replace, asdict

TURN = 35


@dataclass(frozen=True)
class Flight:
    id: str
    tail: str
    origin: str
    destination: str
    departure: int
    duration: int
    fleet: str = "A320"


def schedule():
    cities = ["ADB", "AYT", "ESB", "BJV", "DLM"]
    flights = []
    for i in range(10):
        start = 360 + i * 12
        city = cities[i % len(cities)]
        for leg in range(4):
            flights.append(Flight(f"AO{i * 4 + leg + 1:03}", f"SIM-{i + 1:02}",
                                  "SAW" if leg % 2 == 0 else city,
                                  city if leg % 2 == 0 else "SAW",
                                  start + leg * 125, 75))
    return flights


def simulate(flights, disrupted, delay):
    if not any(f.id == disrupted for f in flights):
        raise ValueError("Unknown flight")
    if not isinstance(delay, int) or not 0 <= delay <= 240:
        raise ValueError("Delay must be an integer between 0 and 240")
    state, rows = {}, []
    for f in sorted(flights, key=lambda f: (f.departure, f.id)):
        location, ready = state.get(f.tail, (f.origin, 0))
        if location != f.origin:
            raise ValueError(f"Aircraft continuity violation for {f.id}")
        actual = max(f.departure + (delay if f.id == disrupted else 0), ready)
        rows.append(dict(asdict(f), actual=actual, delay=actual - f.departure,
                         arrival=actual + f.duration))
        state[f.tail] = (f.destination, actual + f.duration + TURN)
    return rows


def recover(flights, disrupted, delay):
    baseline = simulate(flights, disrupted, delay)
    best, best_rows, decision = flights, baseline, None
    score = sum(r["delay"] for r in baseline)
    # Exchange complete remaining rotations, preserving spatial continuity.
    # Both tails must use the same fleet and start their suffix at the same station.
    ordered = sorted(flights, key=lambda f: (f.departure, f.id))
    event = next(f.departure for f in flights if f.id == disrupted)
    for i, a in enumerate(ordered):
        for b in ordered[i + 1:]:
            if (a.tail == b.tail or a.origin != b.origin or a.fleet != b.fleet
                    or min(a.departure, b.departure) <= event):
                continue
            candidate = [replace(f, tail=b.tail) if f.tail == a.tail and f.departure >= a.departure
                         else replace(f, tail=a.tail) if f.tail == b.tail and f.departure >= b.departure
                         else f for f in flights]
            try:
                rows = simulate(candidate, disrupted, delay)
            except ValueError:
                continue
            cost = sum(r["delay"] for r in rows)
            if cost < score:
                best, best_rows, score = candidate, rows, cost
                decision = dict(tails=[a.tail, b.tail], starts=[a.id, b.id],
                                station=a.origin)
    return dict(baseline=baseline, recovered=best_rows, decision=decision,
                metrics=dict(baseline_delay=sum(r["delay"] for r in baseline),
                             recovered_delay=score,
                             saved_minutes=sum(r["delay"] for r in baseline) - score,
                             affected_before=sum(r["delay"] > 0 for r in baseline),
                             affected_after=sum(r["delay"] > 0 for r in best_rows)))
