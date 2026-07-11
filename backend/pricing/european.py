"""
欧式期权定价模型 - Black-Scholes-Merton (BSM)

适用于只能在到期日行权的欧式期权。
公式:
    Call = S * N(d1) - K * e^(-rT) * N(d2)
    Put  = K * e^(-rT) * N(-d2) - S * N(-d1)
其中:
    d1 = [ln(S/K) + (r + sigma^2/2) * T] / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)
"""
import numpy as np
from scipy.stats import norm


def black_scholes(S: float, K: float, T: float, r: float, sigma: float,
                  option_type: str = "call") -> float:
    """
    Black-Scholes-Merton 欧式期权定价

    参数:
        S: 标的资产当前价格
        K: 行权价
        T: 到期时间(年)
        r: 无风险利率(小数,如0.03表示3%)
        sigma: 年化波动率(小数,如0.25表示25%)
        option_type: "call" 或 "put"

    返回:
        期权理论价格
    """
    if T <= 0:
        # 到期日期权价值
        if option_type == "call":
            return max(S - K, 0.0)
        else:
            return max(K - S, 0.0)

    if sigma <= 0:
        # 波动率为0时期权价值
        if option_type == "call":
            return max(S * np.exp(-r * 0) - K * np.exp(-r * T), 0.0)
        else:
            return max(K * np.exp(-r * T) - S, 0.0)

    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "call":
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:  # put
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    return float(max(price, 0.0))
