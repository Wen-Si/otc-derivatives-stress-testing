"""
压力测试路由(含历史场景支持)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, StressScenario, StressShock, StressResult, Position
from schemas import StressTestRequest
from services.stress_engine import run_stress_test
from services.report_service import generate_report
from historical_scenarios import (
    get_scenario_definitions,
    get_all_historical_scenarios,
    build_historical_scenario,
    HISTORICAL_SCENARIOS,
    _get_fallback_scenario,
)

router = APIRouter()


# ============ 历史场景接口 ============

@router.get("/historical-scenarios")
async def list_historical_scenarios():
    """获取所有历史压力测试场景定义"""
    return {"success": True, "count": len(HISTORICAL_SCENARIOS), "scenarios": get_scenario_definitions()}


@router.get("/historical-scenarios/all/data")
async def get_all_historical_scenarios_with_data():
    """获取所有历史场景(含Tushare真实市场数据)"""
    try:
        scenarios = await get_all_historical_scenarios()
        return {"success": True, "count": len(scenarios), "scenarios": scenarios}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/historical-scenarios/{scenario_id}")
async def get_historical_scenario_detail(scenario_id: str):
    """获取某个历史场景的详细信息(含Tushare真实市场数据)"""
    scenario_def = next((s for s in HISTORICAL_SCENARIOS if s["id"] == scenario_id), None)
    if not scenario_def:
        raise HTTPException(status_code=404, detail=f"历史场景不存在: {scenario_id}")
    try:
        scenario = await build_historical_scenario(scenario_def)
        return {"success": True, "scenario": scenario}
    except Exception as e:
        fallback = _get_fallback_scenario(scenario_def, str(e))
        return {"success": True, "scenario": fallback, "using_fallback": True}


@router.post("/historical-scenarios/{scenario_id}/run")
async def run_historical_scenario(scenario_id: str, db: Session = Depends(get_db)):
    """执行历史场景压力测试"""
    scenario_def = next((s for s in HISTORICAL_SCENARIOS if s["id"] == scenario_id), None)
    if not scenario_def:
        raise HTTPException(status_code=404, detail=f"历史场景不存在: {scenario_id}")
    try:
        scenario_data = await build_historical_scenario(scenario_def)
    except Exception as e:
        scenario_data = _get_fallback_scenario(scenario_def, str(e))
    result = await run_stress_test(db, scenario_data["scenario"])
    report = await generate_report(result)
    return {
        "success": True,
        "scenario_id": result["scenario_id"],
        "scenario_name": result["scenario_name"],
        "description": result.get("description", ""),
        "historical_id": scenario_id,
        "event_type": scenario_def["event_type"],
        "severity": scenario_def["severity"],
        "start_date": scenario_def["start_date"],
        "end_date": scenario_def["end_date"],
        "market_data": scenario_data.get("market_data", {}),
        "current_factors": result["current_factors"],
        "stressed_factors": result["stressed_factors"],
        "shocks": result["shocks"],
        "results": result["results"],
        "total_original_value": result["total_original_value"],
        "total_stressed_value": result["total_stressed_value"],
        "total_pnl": result["total_pnl"],
        "total_pnl_pct": result["total_pnl_pct"],
        "n_positions": result["n_positions"],
        "rsi_applied": result.get("rsi_applied"),
        "report": report,
    }


# ============ 自定义压力测试接口 ============

@router.post("/stress-test/run")
async def run_stress(request: StressTestRequest, db: Session = Depends(get_db)):
    """
    执行压力测试

    请求体:
        scenario: 场景数据(含name, description, shocks)
        position_ids: 可选,指定持仓ID
    """
    # 获取持仓
    positions = None
    if request.position_ids:
        positions = db.query(Position).filter(Position.id.in_(request.position_ids)).all()

    # 执行压力测试
    result = await run_stress_test(db, request.scenario, positions)

    # 生成报告
    report = await generate_report(result)

    return {
        "success": True,
        "scenario_id": result["scenario_id"],
        "scenario_name": result["scenario_name"],
        "description": result.get("description", ""),
        "current_factors": result["current_factors"],
        "stressed_factors": result["stressed_factors"],
        "shocks": result["shocks"],
        "results": result["results"],
        "total_original_value": result["total_original_value"],
        "total_stressed_value": result["total_stressed_value"],
        "total_pnl": result["total_pnl"],
        "total_pnl_pct": result["total_pnl_pct"],
        "n_positions": result["n_positions"],
        "rsi_applied": result.get("rsi_applied"),
        "report": report,
    }


@router.get("/stress-test/scenarios")
async def get_scenarios(db: Session = Depends(get_db)):
    """获取所有历史压力测试场景"""
    scenarios = db.query(StressScenario).order_by(StressScenario.created_at.desc()).all()

    result = []
    for s in scenarios:
        shocks = db.query(StressShock).filter(StressShock.scenario_id == s.id).all()
        result.append({
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "ai_generated": s.ai_generated,
            "status": s.status,
            "total_pnl": s.total_pnl,
            "n_shocks": len(shocks),
            "created_at": s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else "",
        })
    return result


@router.get("/stress-test/scenarios/{scenario_id}")
async def get_scenario_detail(scenario_id: int, db: Session = Depends(get_db)):
    """获取某个压力测试场景的详细信息"""
    scenario = db.query(StressScenario).filter(StressScenario.id == scenario_id).first()
    if not scenario:
        return {"success": False, "error": "场景不存在"}

    shocks = db.query(StressShock).filter(StressShock.scenario_id == scenario_id).all()
    results = db.query(StressResult).filter(StressResult.scenario_id == scenario_id).all()

    shock_list = []
    for sh in shocks:
        shock_list.append({
            "factor_name": sh.factor_name,
            "factor_type": sh.factor_type,
            "shock_type": sh.shock_type,
            "shock_value": sh.shock_value,
            "original_value": sh.original_value,
            "shocked_value": sh.shocked_value,
            "description": sh.description,
        })

    result_list = []
    for r in results:
        pos = db.query(Position).filter(Position.id == r.position_id).first()
        result_list.append({
            "position_id": r.position_id,
            "position_name": pos.name if pos else "",
            "option_type": pos.option_type if pos else "",
            "call_put": pos.call_put if pos else "",
            "strike": pos.strike if pos else 0,
            "quantity": pos.quantity if pos else 0,
            "position_direction": pos.position_direction if pos else "",
            "notional": pos.notional if pos else 0,
            "original_value": r.original_value,
            "stressed_value": r.stressed_value,
            "pnl_change": r.pnl_change,
            "pnl_pct": r.pnl_pct,
        })

    total_original = sum(r["original_value"] for r in result_list)
    total_stressed = sum(r["stressed_value"] for r in result_list)

    return {
        "success": True,
        "scenario_id": scenario.id,
        "scenario_name": scenario.name,
        "description": scenario.description,
        "user_query": scenario.user_query,
        "ai_generated": scenario.ai_generated,
        "status": scenario.status,
        "created_at": scenario.created_at.strftime("%Y-%m-%d %H:%M:%S") if scenario.created_at else "",
        "shocks": shock_list,
        "results": result_list,
        "total_original_value": round(total_original, 2),
        "total_stressed_value": round(total_stressed, 2),
        "total_pnl": scenario.total_pnl,
        "total_pnl_pct": round(
            (scenario.total_pnl / abs(total_original)) if abs(total_original) > 1e-6 else 0.0, 4
        ),
    }
