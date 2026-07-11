"""
压力测试引擎

负责:
1. 应用风险因子冲击,计算冲击后的风险因子值
2. 对每个持仓进行原始估值和压力估值
3. 计算各持仓的盈亏变化
4. 汇总压力测试结果
"""
from datetime import datetime
from sqlalchemy.orm import Session
from database import Position, RiskFactor, StressScenario, StressShock, StressResult
from pricing import price_option
from services.rsi_engine import get_current_params
import services.market_data as market_data


def _time_to_maturity(maturity_date: datetime) -> float:
    """计算到期时间(年)"""
    if isinstance(maturity_date, str):
        maturity_date = datetime.strptime(maturity_date, "%Y-%m-%d")
    delta = maturity_date - datetime.now()
    return max(delta.total_seconds() / (365.25 * 24 * 3600), 0.0)


def apply_shocks(risk_factors: dict, shocks: list) -> dict:
    """
    应用风险因子冲击,计算冲击后的值

    参数:
        risk_factors: 当前风险因子 {"price": ..., "volatility": ..., "risk_free_rate": ...}
        shocks: 冲击列表 [{"factor_type": ..., "shock_type": ..., "shock_value": ...}, ...]

    返回:
        冲击后的风险因子值
    """
    stressed = risk_factors.copy()

    for shock in shocks:
        factor_type = shock.get("factor_type", "")
        shock_type = shock.get("shock_type", "absolute")
        shock_value = shock.get("shock_value", 0.0)

        original = stressed.get(factor_type, 0.0)

        if shock_type == "relative":
            # 相对变动: new = old * (1 + shock_value)
            stressed[factor_type] = original * (1.0 + shock_value)
        else:
            # 绝对变动: new = old + shock_value
            stressed[factor_type] = original + shock_value

        # 确保非负
        if factor_type in ["price", "volatility"]:
            stressed[factor_type] = max(stressed[factor_type], 0.0001)

    return stressed


def value_position(position: Position, risk_factors: dict,
                   model_params: dict = None, calibration: dict = None) -> float:
    """
    对单个持仓进行估值

    参数:
        position: 持仓对象
        risk_factors: {"price": S, "volatility": sigma, "risk_free_rate": r}
        model_params: RSI优化后的模型参数(可选)
        calibration: RSI校准系数(可选,按期权类型校正系统性偏差)
    """
    import json

    S = risk_factors.get("price", 0.0)
    sigma = risk_factors.get("volatility", 0.25)
    r = risk_factors.get("risk_free_rate", 0.025)

    K = position.strike
    T = _time_to_maturity(position.maturity_date)
    call_put = position.call_put

    # 构建定价参数(基础参数)
    pricing_kwargs = {
        "observation_type": position.observation_type or "arithmetic",
        "barrier_type": position.barrier_type or "up_and_out",
        "barrier_level": position.barrier_level or S * 1.1,
        "strike_type": position.observation_type if position.observation_type in ("fixed", "floating") else "fixed",
    }

    # 解析extra_params(JSON),加载奇异期权额外参数
    if position.extra_params:
        try:
            extra = json.loads(position.extra_params)
            pricing_kwargs.update(extra)
        except (json.JSONDecodeError, TypeError):
            pass

    # 单张期权价格(应用RSI优化后的模型参数)
    option_price = price_option(
        option_type=position.option_type,
        S=S,
        K=K,
        T=T,
        r=r,
        sigma=sigma,
        call_put=call_put,
        model_params=model_params,
        **pricing_kwargs,
    )

    # 应用RSI校准系数(校正系统性偏差)
    if calibration:
        cal_factor = calibration.get(position.option_type, 1.0)
        option_price = option_price * cal_factor

    # 总价值 = 单张价格 * 合约数量 * 方向
    direction = 1.0 if position.position_direction == "long" else -1.0
    total_value = option_price * position.quantity * direction

    return total_value


async def run_stress_test(db: Session, scenario_data: dict, positions: list = None) -> dict:
    """
    执行压力测试

    参数:
        db: 数据库会话
        scenario_data: {"name": ..., "description": ..., "shocks": [...]}
        positions: 持仓列表(如果为None则从数据库获取)

    返回:
        压力测试结果字典
    """
    # 1. 获取当前风险因子(从市场数据)
    try:
        market_data_info = await market_data.get_all_market_data()
        current_factors = {
            "price": market_data_info["underlying"]["current_price"],
            "volatility": market_data_info["volatility"]["value"],
            "risk_free_rate": market_data_info["risk_free_rate"]["value"],
        }
    except Exception:
        # 如果无法获取市场数据,使用默认值
        current_factors = {
            "price": 5500.0,
            "volatility": 0.25,
            "risk_free_rate": 0.025,
        }

    # 2. 应用冲击
    shocks = scenario_data.get("shocks", [])
    stressed_factors = apply_shocks(current_factors, shocks)

    # 为每个冲击补充原始值和冲击后值
    for shock in shocks:
        ft = shock.get("factor_type", "")
        shock["original_value"] = current_factors.get(ft, 0.0)
        shock["shocked_value"] = stressed_factors.get(ft, 0.0)

    # 3. 获取持仓
    if positions is None:
        positions = db.query(Position).all()

    # 3.5 加载RSI优化参数(自我进化后的模型参数与校准系数)
    rsi_model_params, rsi_calibration = get_current_params(db)

    # 4. 对每个持仓进行原始估值和压力估值
    results = []
    total_original = 0.0
    total_stressed = 0.0

    for pos in positions:
        original_value = value_position(pos, current_factors,
                                        model_params=rsi_model_params,
                                        calibration=rsi_calibration)
        stressed_value = value_position(pos, stressed_factors,
                                        model_params=rsi_model_params,
                                        calibration=rsi_calibration)

        pnl_change = stressed_value - original_value
        pnl_pct = (pnl_change / abs(original_value)) if abs(original_value) > 1e-6 else 0.0

        results.append({
            "position_id": pos.id,
            "position_name": pos.name,
            "option_type": pos.option_type,
            "call_put": pos.call_put,
            "strike": pos.strike,
            "quantity": pos.quantity,
            "position_direction": pos.position_direction,
            "notional": pos.notional,
            "original_value": round(original_value, 2),
            "stressed_value": round(stressed_value, 2),
            "pnl_change": round(pnl_change, 2),
            "pnl_pct": round(pnl_pct, 4),
        })

        total_original += original_value
        total_stressed += stressed_value

    total_pnl = total_stressed - total_original
    total_pnl_pct = (total_pnl / abs(total_original)) if abs(total_original) > 1e-6 else 0.0

    # 5. 保存到数据库
    scenario = StressScenario(
        name=scenario_data.get("name", "自定义场景"),
        description=scenario_data.get("description", ""),
        user_query=scenario_data.get("user_query", ""),
        ai_generated=True,
        status="completed",
        total_pnl=round(total_pnl, 2),
    )
    db.add(scenario)
    db.flush()  # 获取scenario.id

    # 保存冲击
    for shock in shocks:
        db.add(StressShock(
            scenario_id=scenario.id,
            factor_name=shock.get("factor_name", ""),
            factor_type=shock.get("factor_type", ""),
            shock_type=shock.get("shock_type", "absolute"),
            shock_value=shock.get("shock_value", 0.0),
            original_value=shock.get("original_value"),
            shocked_value=shock.get("shocked_value"),
            description=shock.get("description", ""),
        ))

    # 保存结果
    for r in results:
        pos = db.query(Position).filter(Position.id == r["position_id"]).first()
        if pos:
            db.add(StressResult(
                scenario_id=scenario.id,
                position_id=pos.id,
                original_value=r["original_value"],
                stressed_value=r["stressed_value"],
                pnl_change=r["pnl_change"],
                pnl_pct=r["pnl_pct"],
            ))

    db.commit()

    return {
        "scenario_id": scenario.id,
        "scenario_name": scenario.name,
        "description": scenario.description,
        "current_factors": {k: round(v, 4) for k, v in current_factors.items()},
        "stressed_factors": {k: round(v, 4) for k, v in stressed_factors.items()},
        "shocks": shocks,
        "results": results,
        "total_original_value": round(total_original, 2),
        "total_stressed_value": round(total_stressed, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 4),
        "n_positions": len(results),
        "rsi_applied": {
            "model_params": rsi_model_params,
            "calibration_factors": rsi_calibration,
        },
    }
