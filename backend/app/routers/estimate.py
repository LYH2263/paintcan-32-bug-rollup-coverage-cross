from fastapi import APIRouter, HTTPException
from app.schemas.estimate import EstimateRequest
from app.services.paint_service import (
    PaintService, EmptyRoomListError, DuplicateRoomError, RoomNotFoundError,
)

router = APIRouter()


def _normalize_items(body: EstimateRequest):
    """返回 [{"room_id","coats","coverage"}]；未选任何房间时返回 None 走旧单房。"""
    if body.rooms:
        return [{"room_id": r.room_id, "coats": r.coats, "coverage": r.coverage} for r in body.rooms]
    if body.room_ids is not None:
        return [{"room_id": rid, "coats": body.coats, "coverage": body.coverage} for rid in body.room_ids]
    if body.room_id is not None:
        return None
    return None


@router.post("/estimate")
def post_estimate(body: EstimateRequest):
    with PaintService() as s:
        items = _normalize_items(body)
        if items is None:
            r = s.estimate(body.room_id, body.persist, body.coats, body.coverage)
            if not r:
                raise HTTPException(404, "room not found")
            return r
        try:
            return s.estimate_many(items, body.persist, body.coats, body.coverage)
        except EmptyRoomListError:
            raise HTTPException(422, "room list must not be empty")
        except DuplicateRoomError:
            raise HTTPException(422, "room ids must not repeat")
        except RoomNotFoundError as e:
            raise HTTPException(404, f"room not found: {e.args[0]}")
