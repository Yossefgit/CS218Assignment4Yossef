from datetime import datetime

from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    name: str = Field(min_length=1)
    value: int


class ItemResponse(BaseModel):
    id: int
    name: str
    value: int
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    customer_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    quantity: int = Field(gt=0)


class OrderCreateResponse(BaseModel):
    order_id: str
    status: str


class OrderResponse(BaseModel):
    order_id: str
    customer_id: str
    item_id: str
    quantity: int
    created_at: datetime

    model_config = {"from_attributes": True}