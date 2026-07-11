"""
持仓管理路由
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, Position
from schemas import PositionCreate, PositionResponse
from pricing import price_option
import services.market_data as market_data

router = APIRouter()


async def _get_current_factors():
    """获取当前风险因子(带降级)"""
    try:
        md = await market_data.get_all_market_data()
        return {
            "price": md["underlying"]["current_price"],
            "volatility": md["volatility"]["value"],
            "risk_free_rate": md["risk_free_rate"]["value"],
        }
    except Exception:
        return {"price": 5500.0, "volatility": 0.25, "risk_free_rate": 0.025}


def _time_to_maturity(maturity_date) -> float:
    if isinstance(maturity_date, str):
        maturity_date = datetime.strptime(maturity_date[:10], "%Y-%m-%d")
    delta = maturity_date - datetime.now()
    return max(delta.total_seconds() / (365.25 * 24 * 3600), 0.0)


def _value_position(pos: Position, factors: dict) -> float:
    """估值单个持仓"""
    T = _time_to_maturity(pos.maturity_date)
    if T <= 0:
        S = factors["price"]
        if pos.call_put == "call":
            v = max(S - pos.strike, 0.0)
        else:
            v = max(pos.strike - S, 0.0)
    else:
        v = price_option(
            option_type=pos.option_type,
            S=factors["price"],
            K=pos.strike,
            T=T,
            r=factors["risk_free_rate"],
            sigma=factors["volatility"],
            call_put=pos.call_put,
            observation_type=pos.observation_type or "arithmetic",
            barrier_type=pos.barrier_type or "up_and_out",
            barrier_level=pos.barrier_level or factors["price"] * 1.1,
            strike_type="fixed",
        )
    direction = 1.0 if pos.position_direction == "long" else -1.0
    return v * pos.quantity * direction


@router.get("/positions")
async def get_positions(db: Session = Depends(get_db)):
    """获取所有持仓(含当前估值)"""
    positions = db.query(Position).all()
    factors = await _get_current_factors()

    result = []
    for pos in positions:
        current_value = _value_position(pos, factors)
        result.append({
            "id": pos.id,
            "name": pos.name,
            "option_type": pos.option_type,
            "call_put": pos.call_put,
            "underlying": pos.underlying,
            "underlying_name": pos.underlying_name,
            "strike": pos.strike,
            "maturity_date": pos.maturity_date.strftime("%Y-%m-%d") if pos.maturity_date else "",
            "quantity": pos.quantity,
            "position_direction": pos.position_direction,
            "notional": pos.notional,
            "barrier_type": pos.barrier_type,
            "barrier_level": pos.barrier_level,
            "observation_type": pos.observation_type,
            "entry_price": pos.entry_price,
            "current_value": round(current_value, 2),
        })
    return result


@router.post("/positions")
async def create_position(pos_data: PositionCreate, db: Session = Depends(get_db)):
    """创建新持仓"""
    pos = Position(
        name=pos_data.name,
        option_type=pos_data.option_type,
        call_put=pos_data.call_put,
        underlying=pos_data.underlying,
        underlying_name=pos_data.underlying_name,
        strike=pos_data.strike,
        maturity_date=datetime.strptime(pos_data.maturity_date[:10], "%Y-%m-%d"),
        quantity=pos_data.quantity,
        position_direction=pos_data.position_direction,
        notional=pos_data.notional,
        barrier_type=pos_data.barrier_type,
        barrier_level=pos_data.barrier_level,
        observation_type=pos_data.observation_type,
    )
    db.add(pos)
    db.commit()
    db.refresh(pos)
    return {"id": pos.id, "message": "持仓创建成功"}


@router.delete("/positions/{position_id}")
async def delete_position(position_id: int, db: Session = Depends(get_db)):
    """删除持仓"""
    pos = db.query(Position).filter(Position.id == position_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="持仓不存在")
    db.delete(pos)
    db.commit()
    return {"message": "持仓已删除"}
