"""
历史压力测试场景模块 - 通过Tushare API获取真实市场数据
六大历史场景: 2008金融危机、2015股灾、2016熔断、2018贸易战、2020疫情、2022加息
"""
import numpy as np
import httpx
from config import settings

TUSHARE_API_URL = "https://api.tushare.pro"

HISTORICAL_SCENARIOS = [
    {
        "id": "2008_financial_crisis",
        "name": "2008年全球金融危机",
        "description": "2008年9月雷曼兄弟破产引发全球金融海啸，A股市场遭遇史诗级暴跌。中证500指数在短短两个月内跌幅超过60%，市场波动率急剧攀升，央行紧急降息应对，国债收益率大幅下行。",
        "start_date": "20080901", "end_date": "20081028",
        "pre_start_date": "20080601", "pre_end_date": "20080831",
        "event_type": "系统性金融危机", "severity": "极端",
    },
    {
        "id": "2015_stock_crash",
        "name": "2015年A股股灾",
        "description": "2015年6月至7月，A股经历史无前例的股灾。中证500指数从6月12日的11589点暴跌至7月8日的6444点，跌幅达44.4%。千股跌停频现，市场波动率飙升至极高水平，场外配资爆仓引发连环踩踏。",
        "start_date": "20150612", "end_date": "20150708",
        "pre_start_date": "20150301", "pre_end_date": "20150611",
        "event_type": "市场流动性危机", "severity": "极端",
    },
    {
        "id": "2016_circuit_breaker",
        "name": "2016年A股熔断危机",
        "description": "2016年1月4日，A股熔断机制正式实施首日即触发。沪深300指数在1月4日和1月7日两次触发7%熔断阈值，仅4个交易日中证500指数暴跌约18%。恐慌情绪极度蔓延，波动率短期飙升，1月8日熔断机制被紧急叫停。",
        "start_date": "20160104", "end_date": "20160107",
        "pre_start_date": "20151201", "pre_end_date": "20151231",
        "event_type": "机制性恐慌", "severity": "严重",
    },
    {
        "id": "2018_trade_war",
        "name": "2018年中美贸易战",
        "description": "2018年3月美国对华发起301调查，中美贸易战全面升级。中证500指数全年下跌33.32%，从3月高点持续阴跌至10月低点。市场波动率温和上升，央行货币政策边际宽松，国债收益率有所下行。",
        "start_date": "20180322", "end_date": "20181019",
        "pre_start_date": "20180101", "pre_end_date": "20180321",
        "event_type": "地缘政治冲突", "severity": "严重",
    },
    {
        "id": "2020_covid19",
        "name": "2020年新冠疫情冲击",
        "description": "2020年1月新冠疫情爆发，A股春节后首日(2月3日)暴跌7.72%，超3000股跌停。中证500指数在18个交易日内最大回撤约15%。波动率短期飙升后迅速回落，避险情绪推动国债收益率下行约30bp，随后V型反转。",
        "start_date": "20200120", "end_date": "20200323",
        "pre_start_date": "20191101", "pre_end_date": "20200117",
        "event_type": "突发公共卫生事件", "severity": "严重",
    },
    {
        "id": "2022_fed_rate_hike",
        "name": "2022年美联储加息与俄乌冲突",
        "description": "2022年2月俄乌冲突爆发叠加以美联储激进加息，A股大幅回调。上证指数全年下跌15.13%，中证500指数同期跌幅约20%。市场波动率上升，中美利差倒挂，国内国债收益率小幅上行后回落。",
        "start_date": "20220224", "end_date": "20220427",
        "pre_start_date": "20211201", "pre_end_date": "20220223",
        "event_type": "地缘冲突+货币紧缩", "severity": "严重",
    },
]


async def _tushare_request(api_name, params=None, fields=""):
    payload = {"api_name": api_name, "token": settings.TUSHARE_TOKEN, "params": params or {}, "fields": fields}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(TUSHARE_API_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"Tushare API错误: {data.get('msg', '未知错误')}")
        return data.get("data", {})


async def fetch_historical_index_data(ts_code, start_date, end_date):
    data = await _tushare_request("index_daily", {"ts_code": ts_code, "start_date": start_date, "end_date": end_date}, "ts_code,trade_date,close,pct_chg,vol,amount")
    items = data.get("items", [])
    fields_list = data.get("fields", [])
    records = [dict(zip(fields_list, item)) for item in items]
    records.sort(key=lambda x: x["trade_date"])
    return records


def calculate_price_change(records):
    if not records:
        return {"start_price": 0, "end_price": 0, "change_pct": 0, "max_drawdown": 0}
    closes = [float(r["close"]) for r in records]
    start_price, end_price = closes[0], closes[-1]
    change_pct = (end_price - start_price) / start_price
    peak = closes[0]
    max_dd = 0
    for c in closes:
        if c > peak:
            peak = c
        dd = (c - peak) / peak
        if dd < max_dd:
            max_dd = dd
    return {"start_price": round(start_price, 2), "end_price": round(end_price, 2), "change_pct": round(change_pct, 4), "max_drawdown": round(max_dd, 4)}


def calculate_volatility(records):
    if len(records) < 2:
        return 0.25
    closes = [float(r["close"]) for r in records]
    daily_returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0:
            daily_returns.append(np.log(closes[i] / closes[i - 1]))
    if len(daily_returns) < 5:
        return 0.25
    return float(np.std(daily_returns, ddof=1) * np.sqrt(252))


async def build_historical_scenario(scenario_def):
    ts_code = settings.UNDERLYING_INDEX
    try:
        pre_records = await fetch_historical_index_data(ts_code, scenario_def["pre_start_date"], scenario_def["pre_end_date"])
        pre_volatility = calculate_volatility(pre_records)
        crisis_records = await fetch_historical_index_data(ts_code, scenario_def["start_date"], scenario_def["end_date"])
        if crisis_records:
            price_info = calculate_price_change(crisis_records)
            crisis_volatility = calculate_volatility(crisis_records)
            price_change_pct = price_info["change_pct"]
        else:
            price_change_pct = -0.30
            crisis_volatility = pre_volatility + 0.10
        vol_change = crisis_volatility - pre_volatility
        if vol_change < 0:
            vol_change = abs(vol_change) * 0.5
    except Exception:
        return _get_fallback_scenario(scenario_def, "Tushare API调用失败或频率限制")

    treasury_changes = {
        "2008_financial_crisis": -0.0150,
        "2015_stock_crash": -0.0020,
        "2016_circuit_breaker": -0.0010,
        "2018_trade_war": -0.0040,
        "2020_covid19": -0.0030,
        "2022_fed_rate_hike": 0.0030,
    }
    treasury_change = treasury_changes.get(scenario_def["id"], 0.0)

    price_desc = f"下跌{abs(price_change_pct*100):.1f}%" if price_change_pct < 0 else f"上涨{price_change_pct*100:.1f}%"
    treasury_desc = f"{'上升' if treasury_change > 0 else '下降'}{abs(treasury_change*10000):.0f}个bp"

    shocks = [
        {"factor_name": settings.UNDERLYING_NAME, "factor_type": "price", "shock_type": "relative", "shock_value": round(price_change_pct, 4), "description": f"指数{price_desc}"},
        {"factor_name": "年化波动率", "factor_type": "volatility", "shock_type": "absolute", "shock_value": round(vol_change, 4), "description": f"波动率上升{vol_change*100:.1f}个百分点"},
        {"factor_name": "国债收益率(无风险利率)", "factor_type": "risk_free_rate", "shock_type": "absolute", "shock_value": round(treasury_change, 4), "description": treasury_desc},
    ]
    return {
        "id": scenario_def["id"], "name": scenario_def["name"],
        "description": scenario_def["description"],
        "event_type": scenario_def["event_type"], "severity": scenario_def["severity"],
        "start_date": scenario_def["start_date"], "end_date": scenario_def["end_date"],
        "scenario": {"name": scenario_def["name"], "description": scenario_def["description"], "shocks": shocks},
        "market_data": {"pre_volatility": round(pre_volatility, 4), "crisis_volatility": round(crisis_volatility, 4), "price_change_pct": round(price_change_pct, 4)}
    }


def _get_fallback_scenario(scenario_def, error_msg=""):
    fallback_data = {
        "2008_financial_crisis": {"price": -0.60, "vol_change": 0.18, "treasury": -0.015},
        "2015_stock_crash": {"price": -0.444, "vol_change": 0.15, "treasury": -0.002},
        "2016_circuit_breaker": {"price": -0.18, "vol_change": 0.10, "treasury": -0.001},
        "2018_trade_war": {"price": -0.333, "vol_change": 0.06, "treasury": -0.004},
        "2020_covid19": {"price": -0.15, "vol_change": 0.10, "treasury": -0.003},
        "2022_fed_rate_hike": {"price": -0.20, "vol_change": 0.06, "treasury": 0.003},
    }
    data = fallback_data.get(scenario_def["id"], {"price": -0.20, "vol_change": 0.08, "treasury": 0.0})
    price_desc = f"下跌{abs(data['price']*100):.1f}%" if data['price'] < 0 else f"上涨{data['price']*100:.1f}%"
    treasury_desc = f"{'上升' if data['treasury'] > 0 else '下降'}{abs(data['treasury']*10000):.0f}个bp"
    shocks = [
        {"factor_name": settings.UNDERLYING_NAME, "factor_type": "price", "shock_type": "relative", "shock_value": data["price"], "description": f"指数{price_desc}"},
        {"factor_name": "年化波动率", "factor_type": "volatility", "shock_type": "absolute", "shock_value": data["vol_change"], "description": f"波动率上升{data['vol_change']*100:.1f}个百分点"},
        {"factor_name": "国债收益率(无风险利率)", "factor_type": "risk_free_rate", "shock_type": "absolute", "shock_value": data["treasury"], "description": treasury_desc},
    ]
    return {
        "id": scenario_def["id"], "name": scenario_def["name"],
        "description": scenario_def["description"],
        "event_type": scenario_def["event_type"], "severity": scenario_def["severity"],
        "start_date": scenario_def["start_date"], "end_date": scenario_def["end_date"],
        "scenario": {"name": scenario_def["name"], "description": scenario_def["description"], "shocks": shocks},
        "market_data": {"note": f"预估值({error_msg})"}, "using_fallback": True
    }


def get_scenario_definitions():
    return [{"id": s["id"], "name": s["name"], "description": s["description"], "event_type": s["event_type"], "severity": s["severity"], "start_date": s["start_date"], "end_date": s["end_date"]} for s in HISTORICAL_SCENARIOS]


async def get_all_historical_scenarios():
    results = []
    for scenario_def in HISTORICAL_SCENARIOS:
        try:
            scenario = await build_historical_scenario(scenario_def)
            results.append(scenario)
        except Exception as e:
            results.append(_get_fallback_scenario(scenario_def, str(e)))
    return results
