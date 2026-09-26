from datetime import datetime
from pydantic import BaseModel, Field


class ProductOut(BaseModel):
    id: int
    name: str
    ferment_min: int
    bake_min: int
    model_config = {"from_attributes": True}


class OvenOut(BaseModel):
    id: int
    label: str
    capacity_note: str
    model_config = {"from_attributes": True}


class BatchOut(BaseModel):
    id: int
    product_id: int
    oven_id: int
    code: str
    start_min: int
    status: str
    product_name: str | None = None
    oven_label: str | None = None
    ferment_end: int | None = None
    bake_end: int | None = None
    model_config = {"from_attributes": True}


class BatchCreate(BaseModel):
    product_id: int
    oven_id: int
    start_min: int = Field(ge=0, le=24 * 60 - 1)
    code: str | None = None


class GanttBlock(BaseModel):
    batch_id: int
    code: str
    oven_id: int
    oven_label: str
    phase: str
    start_min: int
    end_min: int


class ConflictOut(BaseModel):
    id: int
    batch_code: str
    oven_id: int
    detail: str
    created_at: datetime
    model_config = {"from_attributes": True}


class ShortGapOut(BaseModel):
    start_min: int
    end_min: int
    short_by_min: int  # 比所需时长短多少分钟


class WindowOut(BaseModel):
    oven_id: int
    oven_label: str
    start_min: int
    end_min: int
    duration_min: int
    ferment_end: int  # 发酵止，与同开工排入甘特的发酵段端点一致
    bake_end: int  # 烘烤止，与同开工排入甘特的烘烤段端点一致
    short_gaps: list[ShortGapOut] = []  # 更早但短于整段时长的空隙
