from pydantic import BaseModel, Field


class RoomEstimateInput(BaseModel):
    room_id: int
    coats: int | None = Field(default=None, gt=0)
    coverage: float | None = Field(default=None, gt=0)


class EstimateRequest(BaseModel):
    # 旧单房接口
    room_id: int | None = None
    # 多房间：room_ids 用统一 coats/coverage；rooms 支持分房涂布率遍数
    room_ids: list[int] | None = None
    rooms: list[RoomEstimateInput] | None = None
    coats: int | None = Field(default=None, gt=0)
    coverage: float | None = Field(default=None, gt=0)
    persist: bool = True
