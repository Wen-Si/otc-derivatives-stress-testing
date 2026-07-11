"""
定价与Greeks API路由

提供期权定价和希腊字母计算的API接口:
1. 查询所有支持的期权类型
2. 计算期权价格
3. 计算希腊字母(完整14个或简版5个)
4. 批量计算多个期权的价格和Greeks
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db, Position
from pricing import price_option, get_greeks, get_all_option_types, get_option_type_name, OPTION_TYPE_NAMES
from services.rsi_engine import get_current_params
from services.stress_engine import _time_to_maturity
import services.market_data as market_data

router = APIRouter()


@router.get("/pricing/option-types")
async def list_option_types():
    """获取所有支持的期权类型(19种)"""
    return {
        "count": len(OPTION_TYPE_NAMES),
        "types": [
            {"type": k, "name": v}
            for k, v in OPTION_TYPE_NAMES.items()
        ],
    }


@router.post("/pricing/calculate")
async def calculate_price(
    option_type: str = Query(..., description="期权类型"),
    S: float = Query(..., description="标的资产价格"),
    K: float = Query(..., description="行权价"),
    T: float = Query(..., description="到期时间(年)"),
    r: float = Query(0.025, description="无风险利率"),
    sigma: float = Query(0.25, description="年化波动率"),
    call_put: str = Query("call", description="call/put"),
    db: Session = Depends(get_db),
):
    """计算单个期权价格"""
    try:
        model_params, _ = get_current_params(db)
        price = price_option(option_type, S, K, T, r, sigma, call_put,
                            model_params=model_params)
        return {
            "success": True,
            "option_type": option_type,
            "option_name": get_option_type_name(option_type),
            "price": round(price, 6),
            "inputs": {"S": S, "K": K, "T": T, "r": r, "sigma": sigma, "call_put": call_put},
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"定价计算失败: {str(e)}")


@router.post("/pricing/greeks")
async def calculate_greeks_api(
    option_type: str = Query(..., description="期权类型"),
    S: float = Query(..., description="标的资产价格"),
    K: float = Query(..., description="行权价"),
    T: float = Query(..., description="到期时间(年)"),
    r: float = Query(0.025, description="无风险利率"),
    sigma: float = Query(0.25, description="年化波动率"),
    call_put: str = Query("call", description="call/put"),
    full: bool = Query(True, description="True=完整14个Greeks, False=简版5个"),
    db: Session = Depends(get_db),
):
    """计算期权希腊字母(支持14种Greeks)"""
    try:
        greeks = get_greeks(option_type, S, K, T, r, sigma, call_put, full=full)
        return {
            "success": True,
            "option_type": option_type,
            "option_name": get_option_type_name(option_type),
            "greeks": greeks,
            "inputs": {"S": S, "K": K, "T": T, "r": r, "sigma": sigma, "call_put": call_put},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Greeks计算失败: {str(e)}")


@router.get("/pricing/position/{position_id}")
async def get_position_pricing(position_id: int, db: Session = Depends(get_db)):
    """获取某持仓的当前估值和Greeks"""
    pos = db.query(Position).filter(Position.id == position_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail=f"持仓不存在: {position_id}")

    try:
        market = await market_data.get_all_market_data()
        S = market["underlying"]["current_price"]
        sigma = market["volatility"]["value"]
        r = market["risk_free_rate"]["value"]
    except Exception:
        S, sigma, r = 5500.0, 0.25, 0.025

    K = pos.strike
    T = _time_to_maturity(pos.maturity_date)
    call_put = pos.call_put

    model_params, calibration = get_current_params(db)

    import json
    pricing_kwargs = {
        "observation_type": pos.observation_type or "arithmetic",
        "barrier_type": pos.barrier_type or "up_and_out",
        "barrier_level": pos.barrier_level or S * 1.1,
        "strike_type": pos.observation_type if pos.observation_type in ("fixed", "floating") else "fixed",
    }
    if pos.extra_params:
        try:
            extra = json.loads(pos.extra_params)
            pricing_kwargs.update(extra)
        except (json.JSONDecodeError, TypeError):
            pass

    price = price_option(pos.option_type, S, K, T, r, sigma, call_put,
                        model_params=model_params, **pricing_kwargs)
    greeks = get_greeks(pos.option_type, S, K, T, r, sigma, call_put, full=True, **pricing_kwargs)

    if calibration:
        cal_factor = calibration.get(pos.option_type, 1.0)
        price = price * cal_factor

    direction = 1.0 if pos.position_direction == "long" else -1.0
    total_value = price * pos.quantity * direction

    return {
        "success": True,
        "position_id": pos.id,
        "position_name": pos.name,
        "option_type": pos.option_type,
        "option_name": get_option_type_name(pos.option_type),
        "call_put": pos.call_put,
        "strike": pos.strike,
        "quantity": pos.quantity,
        "position_direction": pos.position_direction,
        "market_data": {"S": round(S, 2), "sigma": round(sigma, 4), "r": round(r, 4)},
        "unit_price": round(price, 6),
        "total_value": round(total_value, 2),
        "greeks": greeks,
        "rsi_applied": {
            "model_params": model_params,
            "calibration_factors": calibration,
        },
    }


@router.get("/pricing/positions/all-greeks")
async def get_all_positions_greeks(db: Session = Depends(get_db)):
    """获取所有持仓的估值和Greeks汇总"""
    positions = db.query(Position).all()
    if not positions:
        return {"success": True, "count": 0, "results": []}

    try:
        market = await market_data.get_all_market_data()
        S = market["underlying"]["current_price"]
        sigma = market["volatility"]["value"]
        r = market["risk_free_rate"]["value"]
    except Exception:
        S, sigma, r = 5500.0, 0.25, 0.025

    model_params, calibration = get_current_params(db)
    import json

    results = []
    for pos in positions:
        K = pos.strike
        T = _time_to_maturity(pos.maturity_date)
        call_put = pos.call_put

        pricing_kwargs = {
            "observation_type": pos.observation_type or "arithmetic",
            "barrier_type": pos.barrier_type or "up_and_out",
            "barrier_level": pos.barrier_level or S * 1.1,
            "strike_type": pos.observation_type if pos.observation_type in ("fixed", "floating") else "fixed",
        }
        if pos.extra_params:
            try:
                extra = json.loads(pos.extra_params)
                pricing_kwargs.update(extra)
            except (json.JSONDecodeError, TypeError):
                pass

        try:
            price = price_option(pos.option_type, S, K, T, r, sigma, call_put,
                                model_params=model_params, **pricing_kwargs)
            greeks = get_greeks(pos.option_type, S, K, T, r, sigma, call_put, full=True, **pricing_kwargs)

            if calibration:
                cal_factor = calibration.get(pos.option_type, 1.0)
                price = price * cal_factor

            direction = 1.0 if pos.position_direction == "long" else -1.0
            total_value = price * pos.quantity * direction

            results.append({
                "position_id": pos.id,
                "position_name": pos.name,
                "option_type": pos.option_type,
                "option_name": get_option_type_name(pos.option_type),
                "call_put": pos.call_put,
                "strike": pos.strike,
                "quantity": pos.quantity,
                "position_direction": pos.position_direction,
                "T": round(T, 4),
                "unit_price": round(price, 6),
                "total_value": round(total_value, 2),
                "greeks": greeks,
            })
        except Exception as e:
            results.append({
                "position_id": pos.id,
                "position_name": pos.name,
                "option_type": pos.option_type,
                "error": str(e),
            })

    return {
        "success": True,
        "count": len(results),
        "market_data": {"S": round(S, 2), "sigma": round(sigma, 4), "r": round(r, 4)},
        "results": results,
    }
