"""
行情数据服务 - 通过Tushare API获取金融数据

获取数据:
1. 中证500指数(000905.SH)最新价格和历史数据
2. 中证500指数年化波动率(基于历史收益率计算)
3. 国债收益率(无风险利率)

包含缓存机制以避免触发Tushare API频率限制。
"""
import numpy as np
import httpx
import time
from datetime import datetime, timedelta
from config import settings


TUSHARE_API_URL = "https://api.tushare.pro"

# 内存缓存
_cache = {
    "data": None,
    "timestamp": 0,
    "ttl": 7200,  # 缓存有效期: 2小时(秒),避免频繁触发Tushare频率限制
}


def clear_cache():
    """清除市场数据缓存(用于强制刷新)"""
    _cache["data"] = None
    _cache["timestamp"] = 0
    _cache["ttl"] = 7200
    print("[市场数据] 缓存已清除")


async def _tushare_request(api_name: str, params: dict = None, fields: str = "",
                           max_retries: int = 2) -> dict:
    """调用Tushare REST API(含频率限制重试)

    重试策略:
    - 频率限制为"次/分钟": 等待65秒后重试
    - 频率限制为"次/小时": 不重试,直接抛出异常(等待时间过长)
    - 权限不足(40101): 不重试,直接抛出异常
    """
    import asyncio

    payload = {
        "api_name": api_name,
        "token": settings.TUSHARE_TOKEN,
        "params": params or {},
        "fields": fields,
    }

    last_error = None
    for attempt in range(max_retries):
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(TUSHARE_API_URL, json=payload)
            resp.raise_for_status()
            result = resp.json()

        code = result.get("code")
        msg = result.get("msg", "")

        if code == 0:
            # 成功
            return result.get("data", {})
        elif code == 40203:
            # 频率超限
            last_error = f"频率超限: {msg}"
            # 判断是分钟级还是小时级限制
            if "小时" in msg or "hour" in msg.lower():
                # 小时级限制,不重试(等待时间过长)
                print(f"[Tushare] {api_name}频率限制为次/小时,跳过重试")
                break
            elif "分钟" in msg or "minute" in msg.lower():
                # 分钟级限制,等待65秒后重试
                if attempt < max_retries - 1:
                    print(f"[Tushare] 频率超限({api_name}),等待65s后重试(第{attempt+1}次)")
                    await asyncio.sleep(65)
                continue
            else:
                # 未知频率限制,默认不重试
                print(f"[Tushare] 未知频率限制({api_name}): {msg}")
                break
        elif code == 40101:
            # 权限不足,不可恢复
            raise Exception(f"Tushare权限不足({api_name}): {msg}")
        else:
            raise Exception(f"Tushare API错误(code={code}): {msg}")

    raise Exception(f"Tushare API失败: {last_error}")


async def get_index_data(ts_code: str = "000905.SH", n_days: int = 250) -> dict:
    """
    获取指数日线数据并计算波动率
    """
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=n_days + 60)).strftime("%Y%m%d")

    data = await _tushare_request(
        "index_daily",
        {"ts_code": ts_code, "start_date": start_date, "end_date": end_date},
        "ts_code,trade_date,close,pct_chg"
    )

    items = data.get("items", [])
    fields = data.get("fields", [])

    if not items:
        raise Exception(f"未获取到指数数据: {ts_code}")

    # 解析数据
    records = []
    for item in items:
        record = dict(zip(fields, item))
        records.append(record)

    # 按日期排序(从旧到新)
    records.sort(key=lambda x: x["trade_date"])

    closes = [float(r["close"]) for r in records]
    current_price = closes[-1] if closes else 0.0
    trade_date = records[-1]["trade_date"] if records else ""

    # 计算日收益率
    daily_returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0:
            daily_returns.append(np.log(closes[i] / closes[i - 1]))

    # 年化波动率 = std(daily_returns) * sqrt(252)
    if len(daily_returns) > 10:
        annualized_vol = float(np.std(daily_returns, ddof=1) * np.sqrt(252))
    else:
        annualized_vol = 0.25  # 默认25%

    # 近30天历史
    recent_history = [
        {"date": r["trade_date"], "close": float(r["close"])}
        for r in records[-30:]
    ]

    return {
        "current_price": current_price,
        "trade_date": trade_date,
        "daily_returns": daily_returns,
        "annualized_volatility": annualized_vol,
        "history": recent_history,
    }


async def get_treasury_yield() -> float:
    """
    获取国债收益率作为无风险利率

    默认返回2.5%(中国10年期国债收益率合理近似)。
    """
    return 0.025


async def get_all_market_data() -> dict:
    """
    获取所有市场数据(价格、波动率、无风险利率)

    使用缓存机制避免频繁调用Tushare API。
    """
    # 检查缓存
    now = time.time()
    if _cache["data"] is not None and (now - _cache["timestamp"]) < _cache["ttl"]:
        return _cache["data"]

    # 缓存过期或不存在,重新获取
    try:
        index_data = await get_index_data(settings.UNDERLYING_INDEX)
        risk_free_rate = await get_treasury_yield()

        result = {
            "underlying": {
                "code": settings.UNDERLYING_INDEX,
                "name": settings.UNDERLYING_NAME,
                "current_price": round(index_data["current_price"], 2),
                "trade_date": index_data["trade_date"],
            },
            "volatility": {
                "name": "中证500年化波动率",
                "value": round(index_data["annualized_volatility"], 4),
                "trade_date": index_data["trade_date"],
            },
            "risk_free_rate": {
                "name": "国债收益率(无风险利率)",
                "value": round(risk_free_rate, 4),
            },
            "price_history": index_data["history"],
        }

        # 更新缓存
        _cache["data"] = result
        _cache["timestamp"] = now

        return result

    except Exception as e:
        # 如果有旧缓存,返回旧数据
        if _cache["data"] is not None:
            print(f"[市场数据] Tushare API失败,使用缓存数据: {e}")
            return _cache["data"]

        # 没有缓存,使用默认值
        print(f"[市场数据] Tushare API失败,使用默认值: {e}")
        default_result = {
            "underlying": {
                "code": settings.UNDERLYING_INDEX,
                "name": settings.UNDERLYING_NAME,
                "current_price": 5500.0,
                "trade_date": datetime.now().strftime("%Y%m%d"),
            },
            "volatility": {
                "name": "中证500年化波动率",
                "value": 0.25,
                "trade_date": "",
            },
            "risk_free_rate": {
                "name": "国债收益率(无风险利率)",
                "value": 0.025,
            },
            "price_history": [],
        }

        # 缓存默认值(短期缓存,避免频繁重试)
        _cache["data"] = default_result
        _cache["timestamp"] = now
        _cache["ttl"] = 300  # 失败时5分钟后重试

        return default_result
