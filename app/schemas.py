from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import OrderStatus


class OrderCreate(BaseModel):
    customer_id: str = Field(min_length=1, max_length=100)
    product_id: str = Field(min_length=1, max_length=100)
    quantity: int = Field(gt=0, le=1_000_000)


class OrderRead(OrderCreate):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    status: OrderStatus
    created_at: datetime
    updated_at: datetime


class OrderCreated(BaseModel):
    order_id: str
    status: OrderStatus


class HealthResponse(BaseModel):
    status: str
    database: str

