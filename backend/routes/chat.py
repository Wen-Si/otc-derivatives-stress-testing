"""
AI聊天路由 - 解析用户自然语言,生成压力测试场景
"""
from fastapi import APIRouter
from schemas import ChatRequest
from services.ai_service import parse_stress_scenario

router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    用户发送自然语言描述,AI解析为结构化压力测试场景

    返回:
        reply: AI回复文本
        scenario: 结构化场景(含风险因子冲击列表)
    """
    try:
        result = await parse_stress_scenario(request.message)
        return {
            "success": True,
            "reply": result.get("reply", ""),
            "scenario": result.get("scenario", {}),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "reply": f"场景解析失败: {str(e)}",
            "scenario": None,
        }
