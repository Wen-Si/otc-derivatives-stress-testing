"""
AI服务 - 智谱GLM-4.5-Flash集成

负责:
1. 解析用户自然语言输入,识别压力测试场景
2. 生成结构化的风险因子冲击方案
3. 生成压力测试分析报告文本
"""
import json
import httpx
from config import settings


SYSTEM_PROMPT = """你是一个场外衍生品压力测试专家助手。你的任务是帮助用户构建压力测试场景。

用户会通过自然语言描述他们想要的压力测试场景(例如"国债收益率上升30个bp"、"沪深300指数下跌10%"等)。
你需要将其解析为结构化的风险因子冲击方案。

涉及的期权标的资产为: 中证500指数(代码000905.SH)
涉及的三大类风险因子:
1. price (标的资产价格): 如"中证500指数下跌10%"
2. volatility (标的资产年化波动率): 如"波动率上升5个百分点"
3. risk_free_rate (无风险利率/国债收益率): 如"国债收益率上升30个bp"

你必须返回JSON格式(不要包含markdown代码块标记),结构如下:
{
    "reply": "对用户场景的自然语言描述和解释",
    "scenario": {
        "name": "简洁的场景名称(不超过20字)",
        "description": "场景的详细描述",
        "shocks": [
            {
                "factor_name": "风险因子名称(中文)",
                "factor_type": "price 或 volatility 或 risk_free_rate",
                "shock_type": "absolute(绝对变动) 或 relative(相对变动百分比)",
                "shock_value": 数值(正数表示上升,负数表示下降),
                "description": "冲击描述(中文,如'下跌10%')"
            }
        ]
    }
}

注意事项:
- shock_type为"relative"时,shock_value是百分比变动(如-0.10表示下跌10%)
- shock_type为"absolute"时,shock_value是绝对变动值:
  - 波动率用小数(如0.05表示5个百分点,即从0.25变到0.30)
  - 国债收益率用小数(如0.003表示30个bp)
- 如果用户描述的场景涉及多个风险因子,请在shocks数组中全部列出
- 如果用户没有明确提到某个风险因子,不要臆造,只解析用户提到的
- 常见场景示例:
  - "市场大跌": 中证500指数下跌10%(relative, -0.10), 波动率上升5个百分点(absolute, 0.05)
  - "利率上升": 国债收益率上升30bp(absolute, 0.003)
  - "极端熊市": 中证500指数下跌20%, 波动率上升10个百分点, 国债收益率上升50bp"""


async def parse_stress_scenario(user_message: str) -> dict:
    """
    调用GLM-4.5-Flash解析用户输入,生成结构化压力测试场景

    参数:
        user_message: 用户的自然语言输入

    返回:
        {"reply": str, "scenario": {"name": str, "description": str, "shocks": [...]}}
    """
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.ZHIPU_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.ZHIPU_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.1,  # 低温度保证输出稳定
        "max_tokens": 2000,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # 清理可能的markdown代码块标记和多余文本
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        # 提取JSON部分(处理GLM可能在JSON前后添加文字的情况)
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            content = json_match.group(0)

        parsed = json.loads(content)

        # 确保返回格式完整
        if "scenario" not in parsed:
            parsed["scenario"] = {"name": "自定义场景", "description": user_message, "shocks": []}
        if "shocks" not in parsed["scenario"]:
            parsed["scenario"]["shocks"] = []
        if "reply" not in parsed:
            parsed["reply"] = "场景已生成"

        return parsed


async def generate_stress_report(scenario_name: str, description: str,
                                  shocks: list, results: list, total_pnl: float,
                                  total_pnl_pct: float) -> str:
    """
    调用GLM生成压力测试报告文本

    参数:
        scenario_name: 场景名称
        description: 场景描述
        shocks: 风险因子冲击列表
        results: 各持仓的压力测试结果
        total_pnl: 总盈亏
        total_pnl_pct: 总盈亏百分比

    返回:
        报告正文(Markdown格式)
    """
    # 构造提示
    shocks_text = "\n".join([
        f"  - {s.get('factor_name', '')}: {s.get('description', '')}"
        f" (类型:{s.get('shock_type', '')}, 变动值:{s.get('shock_value', '')})"
        for s in shocks
    ])

    results_text = "\n".join([
        f"  - {r.get('position_name', '')}: 原始估值{r.get('original_value', 0):.2f},"
        f" 压力估值{r.get('stressed_value', 0):.2f},"
        f" 盈亏变化{r.get('pnl_change', 0):.2f} ({r.get('pnl_pct', 0)*100:.2f}%)"
        for r in results
    ])

    prompt = f"""请根据以下压力测试结果生成一份专业的分析报告(使用Markdown格式):

场景名称: {scenario_name}
场景描述: {description}

风险因子冲击:
{shocks_text}

各持仓压力测试结果:
{results_text}

总体结果: 总盈亏变化 {total_pnl:.2f} ({total_pnl_pct*100:.2f}%)

请包含以下部分:
1. 执行摘要 - 概述压力测试的目的和主要发现
2. 压力场景分析 - 分析各风险因子冲击的含义和市场背景
3. 持仓影响分析 - 分析各持仓受冲击的程度和原因
4. 风险评估结论 - 总结投资组合的风险敞口和改进建议

请使用专业但易懂的语言,篇幅控制在800字左右。"""

    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.ZHIPU_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.ZHIPU_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 3000,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
