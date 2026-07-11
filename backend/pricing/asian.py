"""
亚式期权定价模型 - 蒙特卡洛模拟 + 解析近似(Turnbull-Wakeman)

亚式期权的收益取决于标的资产在观察期内的平均价格。
分为算术平均和几何平均两种:
    - 算术平均亚式期权: 无解析解,使用蒙特卡洛模拟
    - 几何平均亚式期权: 存在解析解(类似BSM)

本模块同时提供两种方法。
"""
import numpy as np
from scipy.stats import norm


def _geometric_asian_analytic(S: float, K: float, T: float, r: float, sigma: float,
                               option_type: str = "call") -> float:
    """
    几何平均亚式期权解析解 (连续观察)

    几何平均亚式期权存在类似BSM的解析公式。
    """
    n = 1  # 连续观察
    sigma_g = sigma / np.sqrt(3)
    mu_g = 0.5 * (r - 0.5 * sigma ** 2 + sigma_g ** 2)

    d1 = (np.log(S / K) + (mu_g + 0.5 * sigma_g ** 2) * T) / (sigma_g * np.sqrt(T))
    d2 = d1 - sigma_g * np.sqrt(T)

    if option_type == "call":
        price = S * np.exp((mu_g - r) * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp((mu_g - r) * T) * norm.cdf(-d1)

    return float(max(price, 0.0))


def asian_option(S: float, K: float, T: float, r: float, sigma: float,
                 option_type: str = "call", observation_type: str = "arithmetic",
                 n_simulations: int = 20000, n_observations: int = 252) -> float:
    """
    亚式期权定价

    参数:
        S: 标的资产当前价格
        K: 行权价
        T: 到期时间(年)
        r: 无风险利率
        sigma: 年化波动率
        option_type: "call" 或 "put"
        observation_type: "arithmetic"(算术平均) 或 "geometric"(几何平均)
        n_simulations: 蒙特卡洛模拟次数(仅算术平均使用)
        n_observations: 观察次数(默认252个交易日)

    返回:
        亚式期权理论价格
    """
    if T <= 0:
        if option_type == "call":
            return max(S - K, 0.0)
        else:
            return max(K - S, 0.0)

    # 几何平均亚式期权使用解析解
    if observation_type == "geometric":
        return _geometric_asian_analytic(S, K, T, r, sigma, option_type)

    # 算术平均亚式期权使用蒙特卡洛模拟
    if sigma <= 0:
        # 波动率为0时标的路径为确定值
        avg_price = S * np.exp(r * T / 2)
        if option_type == "call":
            return max(avg_price - K, 0.0) * np.exp(-r * T)
        else:
            return max(K - avg_price, 0.0) * np.exp(-r * T)

    dt = T / n_observations
    drift = (r - 0.5 * sigma ** 2) * dt
    vol = sigma * np.sqrt(dt)

    # 使用方差减少技术: 对偶变量法
    n_half = n_simulations // 2
    all_payoffs = []

    # 预生成随机数
    Z = np.random.standard_normal((n_half, n_observations))
    Z_anti = -Z  # 对偶变量

    for z_set in [Z, Z_anti]:
        # 模拟价格路径: S_{t+1} = S_t * exp(drift + vol * z)
        log_returns = drift + vol * z_set
        log_prices = np.cumsum(log_returns, axis=1)
        prices = S * np.exp(log_prices)
        # 在初始价格前加上S0
        prices = np.hstack([np.full((z_set.shape[0], 1), S), prices])

        # 计算算术平均价格
        avg_prices = np.mean(prices, axis=1)

        # 计算期权收益
        if option_type == "call":
            payoffs = np.maximum(avg_prices - K, 0.0)
        else:
            payoffs = np.maximum(K - avg_prices, 0.0)

        all_payoffs.append(payoffs)

    # 合并对偶变量的payoff并取平均(控制方差)
    avg_payoff = (np.mean(all_payoffs[0]) + np.mean(all_payoffs[1])) / 2.0
    price = np.exp(-r * T) * avg_payoff

    return float(max(price, 0.0))
