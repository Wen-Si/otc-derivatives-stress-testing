"""
美式期权定价模型 - 二叉树法 (Cox-Ross-Rubinstein)

美式期权可以在到期前任一时间行权,因此需要使用二叉树或有限差分等数值方法定价。
本模块使用CRR二叉树模型,通过反向归纳求解,在每个节点检查是否提前行权更优。

参数说明:
    u = e^(sigma * sqrt(dt))  -- 上涨因子
    d = 1/u                    -- 下跌因子
    p = (e^(r*dt) - d) / (u - d)  -- 风险中性上涨概率
"""
import numpy as np


def american_option(S: float, K: float, T: float, r: float, sigma: float,
                    option_type: str = "call", steps: int = 200) -> float:
    """
    CRR二叉树美式期权定价

    参数:
        S: 标的资产当前价格
        K: 行权价
        T: 到期时间(年)
        r: 无风险利率(小数)
        sigma: 年化波动率(小数)
        option_type: "call" 或 "put"
        steps: 二叉树步数,越多越精确但越慢

    返回:
        美式期权理论价格
    """
    if T <= 0:
        if option_type == "call":
            return max(S - K, 0.0)
        else:
            return max(K - S, 0.0)

    if sigma <= 0:
        # 波动率为0时退化为内在价值折现
        if option_type == "call":
            return max(S - K * np.exp(-r * T), 0.0)
        else:
            return max(K * np.exp(-r * T) - S, 0.0)

    dt = T / steps
    u = np.exp(sigma * np.sqrt(dt))
    d = 1.0 / u
    p = (np.exp(r * dt) - d) / (u - d)
    discount = np.exp(-r * dt)

    # 构建末端节点价格
    ST = np.zeros(steps + 1)
    for i in range(steps + 1):
        ST[i] = S * (u ** (steps - i)) * (d ** i)

    # 末端期权价值
    if option_type == "call":
        option_values = np.maximum(ST - K, 0.0)
    else:
        option_values = np.maximum(K - ST, 0.0)

    # 反向归纳
    for step in range(steps - 1, -1, -1):
        for i in range(step + 1):
            # 持有价值
            hold = discount * (p * option_values[i] + (1 - p) * option_values[i + 1])
            # 当前节点标的价格
            S_current = S * (u ** (step - i)) * (d ** i)
            # 行权价值
            if option_type == "call":
                exercise = max(S_current - K, 0.0)
            else:
                exercise = max(K - S_current, 0.0)
            # 美式期权取持有和行权的较大值
            option_values[i] = max(hold, exercise)

    return float(option_values[0])
