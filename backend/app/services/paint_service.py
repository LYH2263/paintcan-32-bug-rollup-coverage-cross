from app.db import connect
from app.engines.estimate import estimate_room
from app.repositories import openings, rooms, runs, settings


class EmptyRoomListError(ValueError):
    pass


class DuplicateRoomError(ValueError):
    pass


class RoomNotFoundError(LookupError):
    pass


class PaintService:
    def __init__(self): self._c = connect()
    def close(self): self._c.close()
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
    def list_rooms(self): return rooms.list_all(self._c)
    def room_detail(self, rid):
        r = rooms.get(self._c, rid)
        if not r: return None
        return {"room": r, "openings": openings.for_room(self._c, rid)}
    def settings(self): return settings.get_map(self._c)
    def history(self, limit=50):
        return [self._hydrate_run(r) for r in runs.list_recent(self._c, limit)]

    def _hydrate_run(self, row):
        import json
        item = dict(row)
        for key in ("input_json", "result_json"):
            raw = item.get(key)
            try:
                item[key.replace("_json", "")] = json.loads(raw) if raw else None
            except (ValueError, TypeError):
                item[key.replace("_json", "")] = None
        return item

    def _calc_room(self, room_id, coverage, coats):
        """按房间当前门窗与给定涂布率/遍数计算，返回 (房间行, 计算结果)。"""
        detail = self.room_detail(room_id)
        if not detail:
            return None
        r = detail["room"]
        ops = [{"w": o["w"], "h": o["h"]} for o in detail["openings"]]
        calc = estimate_room(r["length"], r["width"], r["height"], ops, coverage, coats)
        return r, calc

    def estimate(self, room_id, persist, coats=None, coverage=None):
        cov, ct = settings.coverage_coats(self._c)
        cov = float(coverage or cov)
        ct = int(coats or ct)
        got = self._calc_room(room_id, cov, ct)
        if not got: return None
        result = got[1]
        rid = runs.insert(self._c, "estimate", {"room_id": room_id, "coats": ct, "coverage": cov}, result, room_id) if persist else None
        return {"run_id": rid, "room_id": room_id, **result}

    def estimate_many(self, items, persist, default_coats=None, default_coverage=None):
        """items: [{"room_id": int, "coats": int|None, "coverage": float|None}, ...]
        统一/分房涂布率遍数 → 分房明细 + 合计。参数非法（空/重复/不存在）整单拒绝，不写记录。"""
        room_ids = [int(i["room_id"]) for i in items]
        if not room_ids:
            raise EmptyRoomListError("room list is empty")
        if len(room_ids) != len(set(room_ids)):
            raise DuplicateRoomError(f"duplicate room ids in {room_ids}")

        cov_def, ct_def = settings.coverage_coats(self._c)
        cov_def = float(default_coverage or cov_def)
        ct_def = int(default_coats or ct_def)

        rows = []
        # 先全部校验/算完再落库：任一房间不存在则整单不产生 calc_runs
        for it in items:
            room_id = int(it["room_id"])
            cov = float(it.get("coverage") or cov_def)
            ct = int(it.get("coats") or ct_def)
            got = self._calc_room(room_id, cov, ct)
            if not got:
                raise RoomNotFoundError(room_id)
            r, calc = got
            # 钉选分房快照：名称、尺寸与当时算得的升数一并存入 result_json
            rows.append({
                "room_id": r["id"], "name": r["name"],
                "length": r["length"], "width": r["width"], "height": r["height"],
                **calc,
            })

        from app.services.rollup_cross import sum_room_totals
        total_liters, total_net = sum_room_totals(rows)
        result = {
            "rooms": rows,
            "total_gross_m2": round(sum(x["gross_m2"] for x in rows), 2),
            "total_openings_m2": round(sum(x["openings_m2"] for x in rows), 2),
            "total_net_m2": total_net,
            "total_liters": total_liters,
        }
        payload = {"rooms": [
            {"room_id": x["room_id"], "coats": x["coats"], "coverage": x["coverage"]}
            for x in rows
        ]}
        run_id = runs.insert(self._c, "estimate_many", payload, result) if persist else None
        return {"run_id": run_id, **result}

    def dashboard(self):
        rs = rooms.list_all(self._c)
        return {"room_count": len(rs), "clean": len([x for x in rs if "种子" not in x["name"] and "多种" not in x["name"]]), "dirty": len([x for x in rs if "多种" in x["name"]])}
