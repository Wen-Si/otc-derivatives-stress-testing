"""
市场数据路由
"""
from fastapi import APIRouter
from services.market_data import get_all_market_data, clear_cache

router = APIRouter()


@router.get("/risk-factors")
async def get_risk_factors():
    """
    获取当前风险因子(扁平格式,供前端直接使用)
    返回: {"index_price": ..., "volatility": ..., "risk_free_rate": ..., ...详情}
    """
    try:
        data = await get_all_market_data()
        return {
            "index_price": data["underlying"]["current_price"],
            "volatility": data["volatility"]["value"],
            "risk_free_rate": data["risk_free_rate"]["value"],
            "underlying_name": data["underlying"]["name"],
            "underlying_code": data["underlying"]["code"],
            "trade_date": data["underlying"]["trade_date"],
            "price_history": data.get("price_history", []),
        }
    except Exception as e:
        return {
            "index_price": 5500.0,
            "volatility": 0.25,
            "risk_free_rate": 0.025,
            "underlying_name": "中证500指数",
            "underlying_code": "000905.SH",
            "trade_date": "",
            "price_history": [],
            "error": str(e),
        }


@router.get("/market-data")
async def get_market_data():
    """获取完整市场数据(含历史价格,嵌套格式)"""
    try:
        data = await get_all_market_data()
        return {
            "success": True,
            "data": data,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": None,
        }


@router.post("/market-data/refresh")
async def refresh_market_data():
    """清除缓存并强制刷新市场数据(重新从Tushare获取)"""
    try:
        clear_cache()
        data = await get_all_market_data()
        return {
            "success": True,
            "message": "市场数据已刷新",
            "data": data,
            "from_cache": False,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "刷新失败,请稍后重试(Tushare API可能有频率限制)",
        }


@router.get("/tushare/status")
async def tushare_status():
    """检查Tushare API连通状态"""
    import httpx
    from config import settings

    try:
        # 快速连通性检查
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://api.tushare.pro")
            server_reachable = resp.status_code == 200

        # 尝试一次轻量API调用
        payload = {
            "api_name": "daily",
            "token": settings.TUSHARE_TOKEN,
            "params": {"ts_code": "000001.SZ", "start_date": "20260701", "end_date": "20260710"},
            "fields": "ts_code,trade_date,close",
        }
        api_ok = False
        api_msg = ""
        record_count = 0
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://api.tushare.pro", json=payload)
            resp.raise_for_status()
            result = resp.json()

        code = result.get("code")
        if code == 0:
            api_ok = True
            api_msg = "Token有效,daily接口可用"
            record_count = len(result.get("data", {}).get("items", []))
        elif code == 40203:
            api_ok = True  # Token有效,只是频率限制
            api_msg = f"Token有效但触发频率限制(1次/分钟): {result.get('msg', '')}"
        elif code == 40101:
            api_ok = False
            api_msg = f"Token权限不足: {result.get('msg', '')}"
        else:
            api_ok = False
            api_msg = f"未知错误(code={code}): {result.get('msg', '')}"

        return {
            "server_reachable": server_reachable,
            "token_valid": api_ok,
            "api_message": api_msg,
            "test_endpoint": "daily (000001.SZ)",
            "record_count": record_count,
            "token_preview": settings.TUSHARE_TOKEN[:8] + "..." + settings.TUSHARE_TOKEN[-4:],
            "cache_ttl": 7200,
            "note": "index_daily接口限制1次/小时,缓存2小时; cn_gdr接口需更高权限; daily接口正常可用",
        }
    except Exception as e:
        return {
            "server_reachable": False,
            "token_valid": False,
            "error": str(e),
        }
