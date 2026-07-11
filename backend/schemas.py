"""
Pydantic数据模型(Schema)
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============ 请求模型 ============

class ChatRequest(BaseModel):
    message: str = Field(..., description="用户自然语言输入")


class ShockItem(BaseModel):
    factor_name: str = ""
    factor_type: str = "price"
    shock_type: str = "absolute"
    shock_value: float = 0.0
    description: str = ""


class StressTestRequest(BaseModel):
    scenario: dict = Field(..., description="压力测试场景数据")
    position_ids: Optional[List[int]] = Field(None, description="指定持仓ID列表,为空则全部")


class PositionCreate(BaseModel):
    name: str
    option_type: str = "european"
    call_put: str = "call"
    underlying: str = "000905.SH"
    underlying_name: str = "中证500指数"
    strike: float
    maturity_date: str
    quantity: float = 1.0
    position_direction: str = "long"
    notional: float = 0.0
    barrier_type: Optional[str] = None
    barrier_level: Optional[float] = None
    observation_type: Optional[str] = None


# ============ 响应模型 ============

class PositionResponse(BaseModel):
    id: int
    name: str
    option_type: str
    call_put: str
    underlying_name: str
    strike: float
    maturity_date: str
    quantity: float
    position_direction: str
    notional: float
    current_value: Optional[float] = None
    entry_price: Optional[float] = None

    class Config:
        from_attributes = True


class MarketDataResponse(BaseModel):
    underlying: dict
    volatility: dict
    risk_free_rate: dict
    price_history: list = []
