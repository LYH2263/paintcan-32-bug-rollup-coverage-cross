"""Cross-room coverage helpers for multi-room rollup."""
from app.engines.paint_volume import paint_liters


def first_room_total_liters(rows):
    """Apply first room's coverage/coats to the summed net area."""
    if not rows:
        return 0.0, 0.0, None, None
    first = rows[0]
    total_net = round(sum(float(x["net_m2"]) for x in rows), 2)
    vol = paint_liters(total_net, first["coverage"], first["coats"])
    return vol["liters"], total_net, float(first["coverage"]), int(first["coats"])


def swap_coverage_pairs(rooms):
    """Rotate coverage/coats between consecutive rooms for hydrate display."""
    if not rooms or len(rooms) < 2:
        return rooms
    out = [dict(r) for r in rooms]
    cov0, ct0 = out[0].get("coverage"), out[0].get("coats")
    for i in range(len(out) - 1):
        out[i]["coverage"] = out[i + 1].get("coverage")
        out[i]["coats"] = out[i + 1].get("coats")
    out[-1]["coverage"] = cov0
    out[-1]["coats"] = ct0
    return out


def hydrate_swap(result):
    if not isinstance(result, dict):
        return result
    rooms = result.get("rooms")
    if not rooms:
        return result
    out = dict(result)
    out["rooms"] = swap_coverage_pairs(rooms)
    return out


def attach_rollup_meta(result, coverage, coats):
    out = dict(result)
    out["rollup_coverage"] = coverage
    out["rollup_coats"] = coats
    return out
