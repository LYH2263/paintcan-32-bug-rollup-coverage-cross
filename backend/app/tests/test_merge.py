import json

import pytest

from app import db as db_mod
from app import seed
from app.repositories import runs
from app.services.paint_service import (
    PaintService, EmptyRoomListError, DuplicateRoomError, RoomNotFoundError,
)


@pytest.fixture
def svc(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test.db")
    seed.init_db()
    with PaintService() as s:
        yield s


def _run_count(s):
    return s._c.execute("SELECT COUNT(*) c FROM calc_runs").fetchone()["c"]


def test_single_room_matches_legacy(svc):
    single = svc.estimate(1, False)
    merged = svc.estimate_many([{"room_id": 1, "coats": None, "coverage": None}], False)
    assert merged["total_liters"] == single["liters"]
    assert merged["rooms"][0]["liters"] == single["liters"]
    assert merged["run_id"] is None


def test_multi_room_total_is_sum_of_per_room(svc):
    r = svc.estimate_many([
        {"room_id": 1, "coats": 2, "coverage": 8},
        {"room_id": 2, "coats": 2, "coverage": 8},
    ], False)
    per = [x["liters"] for x in r["rooms"]]
    assert per == [11.6, 8.48]
    assert r["total_liters"] == round(sum(per), 2)
    assert [x["room_id"] for x in r["rooms"]] == [1, 2]


def test_per_room_coverage_and_coats(svc):
    r = svc.estimate_many([
        {"room_id": 1, "coats": 1, "coverage": 10},
        {"room_id": 2, "coats": None, "coverage": None},
    ], False, default_coats=2, default_coverage=8)
    assert r["rooms"][0]["coats"] == 1 and r["rooms"][0]["coverage"] == 10.0
    assert r["rooms"][1]["coats"] == 2 and r["rooms"][1]["coverage"] == 8.0


def test_empty_list_rejected_without_record(svc):
    before = _run_count(svc)
    with pytest.raises(EmptyRoomListError):
        svc.estimate_many([], False)
    assert _run_count(svc) == before


def test_duplicate_rejected_without_record(svc):
    before = _run_count(svc)
    with pytest.raises(DuplicateRoomError):
        svc.estimate_many([
            {"room_id": 1, "coats": 2, "coverage": 8},
            {"room_id": 1, "coats": 1, "coverage": 9},
        ], True)
    assert _run_count(svc) == before


def test_missing_room_rejected_without_record(svc):
    before = _run_count(svc)
    with pytest.raises(RoomNotFoundError):
        svc.estimate_many([{"room_id": 1}, {"room_id": 999}], True)
    assert _run_count(svc) == before


def test_persist_writes_one_pinned_run(svc):
    before = _run_count(svc)
    r = svc.estimate_many([{"room_id": 1, "coats": 2, "coverage": 8},
                           {"room_id": 2, "coats": 2, "coverage": 8}], True)
    assert _run_count(svc) == before + 1
    assert r["run_id"] is not None

    rows = runs.list_recent(svc._c, 5)
    row = next(x for x in rows if x["id"] == r["run_id"])
    assert row["kind"] == "estimate_many"
    assert row["room_id"] is None
    saved = json.loads(row["result_json"])
    assert saved["total_liters"] == r["total_liters"]
    assert [x["room_id"] for x in saved["rooms"]] == [1, 2]
    old_room2 = next(x for x in saved["rooms"] if x["room_id"] == 2)
    assert old_room2["liters"] == 8.48

    # 改其中一房层高后，旧合并记录的分房升数不得跟着变
    svc._c.execute("UPDATE rooms SET height=4.0 WHERE id=2")
    svc._c.commit()
    rows = runs.list_recent(svc._c, 5)
    saved_after = json.loads(next(x for x in rows if x["id"] == r["run_id"])["result_json"])
    room2_after = next(x for x in saved_after["rooms"] if x["room_id"] == 2)
    assert room2_after["liters"] == old_room2["liters"]
    assert room2_after["height"] == 2.8  # 钉选的是当时的层高

    # 用当前数据重算确实变了，证明旧记录是快照而非实时关联
    fresh = svc.estimate_many([{"room_id": 2, "coats": 2, "coverage": 8}], False)
    assert fresh["rooms"][0]["liters"] != old_room2["liters"]


def test_history_hydrates_json(svc):
    r = svc.estimate_many([{"room_id": 1, "coats": 2, "coverage": 8}], True)
    hist = svc.history(50)
    item = next(x for x in hist if x["id"] == r["run_id"])
    assert item["result"]["total_liters"] == r["total_liters"]
    assert item["input"]["rooms"][0]["room_id"] == 1
