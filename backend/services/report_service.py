"""
报告生成服务

将压力测试结果整理为结构化报告,并调用AI生成分析文本。
"""
import services.ai_service as ai_service


async def generate_report(stress_result: dict) -> dict:
    """
    生成完整的压力测试报告

    参数:
        stress_result: 压力测试结果(from stress_engine.run_stress_test)

    返回:
        {
            "scenario_name": ...,
            "description": ...,
            "summary": {...},
            "shocks": [...],
            "results": [...],
            "ai_analysis": AI生成的分析报告文本,
        }
    """
    # 调用AI生成分析报告
    try:
        ai_analysis = await ai_service.generate_stress_report(
            scenario_name=stress_result["scenario_name"],
            description=stress_result.get("description", ""),
            shocks=stress_result.get("shocks", []),
            results=stress_result.get("results", []),
            total_pnl=stress_result["total_pnl"],
            total_pnl_pct=stress_result["total_pnl_pct"],
        )
    except Exception as e:
        ai_analysis = f"AI报告生成失败: {str(e)}\n\n" + _generate_fallback_report(stress_result)

    return {
        "scenario_name": stress_result["scenario_name"],
        "description": stress_result.get("description", ""),
        "summary": {
            "total_original_value": stress_result["total_original_value"],
            "total_stressed_value": stress_result["total_stressed_value"],
            "total_pnl": stress_result["total_pnl"],
            "total_pnl_pct": stress_result["total_pnl_pct"],
            "n_positions": stress_result["n_positions"],
        },
        "current_factors": stress_result.get("current_factors", {}),
        "stressed_factors": stress_result.get("stressed_factors", {}),
        "shocks": stress_result.get("shocks", []),
        "results": stress_result.get("results", []),
        "ai_analysis": ai_analysis,
    }


def _generate_fallback_report(stress_result: dict) -> str:
    """当AI不可用时的后备报告"""
    shocks_text = "\n".join([
        f"- {s.get('factor_name', '')}: {s.get('description', '')}"
        for s in stress_result.get("shocks", [])
    ])

    results_text = "\n".join([
        f"- {r['position_name']}: 盈亏变化 {r['pnl_change']:.2f} ({r['pnl_pct']*100:.2f}%)"
        for r in stress_result.get("results", [])
    ])

    return f"""# 压力测试报告

## 场景: {stress_result['scenario_name']}

### 风险因子冲击
{shocks_text}

### 持仓影响
{results_text}

### 总体结果
- 原始组合价值: {stress_result['total_original_value']:.2f}
- 压力下组合价值: {stress_result['total_stressed_value']:.2f}
- 总盈亏变化: {stress_result['total_pnl']:.2f} ({stress_result['total_pnl_pct']*100:.2f}%)
"""
