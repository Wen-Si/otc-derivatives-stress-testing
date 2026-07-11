"""
奇异期权定价模型

包含以下奇异期权类型:
1. 障碍期权 (Barrier Options):
   - 敲出期权: up_and_out, down_and_out (触碰障碍后失效)
   - 敲入期权: up_and_in, down_and_in (触碰障碍后生效)
2. 回望期权 (Lookback Options):
   - 固定行权价回望: 收益取决于观察期内最优价格
   - 浮动行权价回望: 行权价为观察期内最优/最差价格

障碍期权存在解析近似公式(连续观察),本模块同时提供解析解和蒙特卡洛模拟。
回望期权使用蒙特卡洛模拟定价。
"""
import numpy as np
from scipy.stats import norm


# ============ 障碍期权 ============

def _barrier_analytic(S: float, K: float, T: float, r: float, sigma: float,
                      H: float, option_type: str, barrier_direction: str, knock: str) -> float:
    """
    障碍期权解析近似公式 (连续观察)

    参数:
        H: 障碍水平
        option_type: "call" 或 "put"
        barrier_direction: "up" 或 "down"
        knock: "in" 或 "out"
    """
    from pricing.european import black_scholes

    # 计算辅助参数
    mu = (r - 0.5 * sigma ** 2) / (sigma ** 2)
    lam = np.log(H / S) / (sigma * np.sqrt(T))
    lam2 = lam ** 2

    # 辅助函数
    def _phi(x, y):
        """累积正态分布辅助函数"""
        return np.exp(-x * y) * norm.cdf((np.log(H / S) + (mu + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T)))

    # 根据障碍类型计算
    # 使用Reiner-Rubinstein公式
    eta = 1 if option_type == "call" else -1
    phi = 1 if barrier_direction == "up" else -1

    # S > H 或 S < H 的不同处理
    if (barrier_direction == "up" and S >= H) or (barrier_direction == "down" and S <= H):
        # 标的已穿越障碍
        if knock == "in":
            # 敲入期权已激活,等同于普通期权
            return black_scholes(S, K, T, r, sigma, option_type)
        else:
            # 敲出期权已失效
            return 0.0

    # 计算d1, d2, d3, d4
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    d3 = (np.log(S / H) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d4 = d3 - sigma * np.sqrt(T)

    # 障碍期权各分量
    S2H = S ** 2 / H ** 2

    # 敲出期权价格
    term1 = eta * S * np.exp(-r * T) * (
        H / S) ** (2 * mu + 2) * norm.cdf(eta * (d3 - 2 * np.log(H / S) / (sigma * np.sqrt(T))))
    term2 = -eta * K * np.exp(-r * T) * (
        H / S) ** (2 * mu) * norm.cdf(eta * (d3 - 2 * np.log(H / S) / (sigma * np.sqrt(T)) - sigma * np.sqrt(T)))

    if knock == "out":
        if (barrier_direction == "up" and option_type == "call") or \
           (barrier_direction == "down" and option_type == "put"):
            # up-and-out call / down-and-out put
            price = (black_scholes(S, K, T, r, sigma, option_type)
                     - S * (H / S) ** (2 * mu + 2) * norm.cdf(d1 - 2 * np.log(H / S) / (sigma * np.sqrt(T)))
                     + K * np.exp(-r * T) * (H / S) ** (2 * mu) * norm.cdf(d2 - 2 * np.log(H / S) / (sigma * np.sqrt(T))))
        elif (barrier_direction == "down" and option_type == "call"):
            # down-and-out call
            if K < H:
                price = (S * norm.cdf(d3) - K * np.exp(-r * T) * norm.cdf(d4)
                         - S * (H / S) ** (2 * mu + 2) * norm.cdf(-d1 + 2 * np.log(H / S) / (sigma * np.sqrt(T)))
                         + K * np.exp(-r * T) * (H / S) ** (2 * mu) * norm.cdf(-d2 + 2 * np.log(H / S) / (sigma * np.sqrt(T))))
            else:
                price = (S * (H / S) ** (2 * mu + 2) * norm.cdf(-d1 + 2 * np.log(H / S) / (sigma * np.sqrt(T)))
                         - K * np.exp(-r * T) * (H / S) ** (2 * mu) * norm.cdf(-d2 + 2 * np.log(H / S) / (sigma * np.sqrt(T)))
                         - S * (H / S) ** (2 * mu + 2) * norm.cdf(-d3 + 2 * np.log(H / S) / (sigma * np.sqrt(T)))
                         + K * np.exp(-r * T) * (H / S) ** (2 * mu) * norm.cdf(-d4 + 2 * np.log(H / S) / (sigma * np.sqrt(T))))
        elif (barrier_direction == "up" and option_type == "put"):
            # up-and-out put
            if K > H:
                price = (-S * norm.cdf(-d3) + K * np.exp(-r * T) * norm.cdf(-d4)
                         + S * (H / S) ** (2 * mu + 2) * norm.cdf(d1 - 2 * np.log(H / S) / (sigma * np.sqrt(T)))
                         - K * np.exp(-r * T) * (H / S) ** (2 * mu) * norm.cdf(d2 - 2 * np.log(H / S) / (sigma * np.sqrt(T))))
            else:
                price = (-S * (H / S) ** (2 * mu + 2) * norm.cdf(d3 - 2 * np.log(H / S) / (sigma * np.sqrt(T)))
                         + K * np.exp(-r * T) * (H / S) ** (2 * mu) * norm.cdf(d4 - 2 * np.log(H / S) / (sigma * np.sqrt(T)))
                         + S * (H / S) ** (2 * mu + 2) * norm.cdf(d1 - 2 * np.log(H / S) / (sigma * np.sqrt(T)))
                         - K * np.exp(-r * T) * (H / S) ** (2 * mu) * norm.cdf(d2 - 2 * np.log(H / S) / (sigma * np.sqrt(T))))
        else:
            price = 0.0
    else:
        # 敲入期权 = 普通期权 - 敲出期权 (出入平价)
        out_price = _barrier_analytic(S, K, T, r, sigma, H, option_type, barrier_direction, "out")
        price = black_scholes(S, K, T, r, sigma, option_type) - out_price

    return float(max(price, 0.0))


def barrier_option_mc(S: float, K: float, T: float, r: float, sigma: float,
                      H: float, barrier_type: str = "up_and_out", option_type: str = "call",
                      n_simulations: int = 20000, n_steps: int = 252) -> float:
    """
    障碍期权蒙特卡洛定价 (离散观察)

    参数:
        S: 标的当前价格
        K: 行权价
        T: 到期时间(年)
        r: 无风险利率
        sigma: 波动率
        H: 障碍水平
        barrier_type: "up_and_out"/"down_and_out"/"up_and_in"/"down_and_in"
        option_type: "call" 或 "put"
        n_simulations: 模拟次数
        n_steps: 每条路径的步数(观察频率)
    """
    if T <= 0:
        if option_type == "call":
            return max(S - K, 0.0)
        else:
            return max(K - S, 0.0)

    dt = T / n_steps
    drift = (r - 0.5 * sigma ** 2) * dt
    vol = sigma * np.sqrt(dt)

    # 对偶变量法
    n_half = n_simulations // 2
    Z = np.random.standard_normal((n_half, n_steps))
    Z_anti = -Z

    all_payoffs = []

    for z_set in [Z, Z_anti]:
        # 模拟价格路径
        log_returns = drift + vol * z_set
        log_prices = np.cumsum(log_returns, axis=1)
        prices = S * np.exp(log_prices)
        prices = np.hstack([np.full((n_half, 1), S), prices])

        # 检查是否触碰障碍
        if "up" in barrier_type:
            touched = np.max(prices, axis=1) >= H
        else:  # down
            touched = np.min(prices, axis=1) <= H

        ST = prices[:, -1]

        # 计算行权收益
        if option_type == "call":
            intrinsic = np.maximum(ST - K, 0.0)
        else:
            intrinsic = np.maximum(K - ST, 0.0)

        # 根据障碍类型确定是否有效
        if "out" in barrier_type:
            # 敲出: 触碰则失效
            payoffs = np.where(touched, 0.0, intrinsic)
        else:
            # 敲入: 触碰则生效
            payoffs = np.where(touched, intrinsic, 0.0)

        all_payoffs.append(payoffs)

    avg_payoff = (np.mean(all_payoffs[0]) + np.mean(all_payoffs[1])) / 2.0
    price = np.exp(-r * T) * avg_payoff

    return float(max(price, 0.0))


def barrier_option(S: float, K: float, T: float, r: float, sigma: float,
                   H: float, barrier_type: str = "up_and_out", option_type: str = "call",
                   n_simulations: int = 20000, n_steps: int = 252) -> float:
    """
    障碍期权定价 (优先解析解,失败则用蒙特卡洛)
    """
    try:
        barrier_direction = barrier_type.split("_")[0]  # up / down
        knock = barrier_type.split("_")[1]  # in / out
        return _barrier_analytic(S, K, T, r, sigma, H, option_type, barrier_direction, knock)
    except Exception:
        return barrier_option_mc(S, K, T, r, sigma, H, barrier_type, option_type,
                                  n_simulations, n_steps)


# ============ 回望期权 ============

def lookback_option(S: float, K: float, T: float, r: float, sigma: float,
                    option_type: str = "call", strike_type: str = "fixed",
                    n_simulations: int = 20000, n_steps: int = 252) -> float:
    """
    回望期权定价 (蒙特卡洛模拟)

    参数:
        S: 标的当前价格
        K: 行权价(fixed类型使用)
        T: 到期时间(年)
        r: 无风险利率
        sigma: 波动率
        option_type: "call" 或 "put"
        strike_type: "fixed"(固定行权价) 或 "floating"(浮动行权价)
        n_simulations: 模拟次数
        n_steps: 路径步数

    收益说明:
        - fixed call: max(S_max - K, 0)  -- 以观察期内最高价卖出
        - fixed put: max(K - S_min, 0)   -- 以观察期内最低价买入
        - floating call: max(S_T - S_min, 0)  -- 以最低价买入,到期价卖出
        - floating put: max(S_max - S_T, 0)    -- 以最高价卖出,到期价买入
    """
    if T <= 0:
        if option_type == "call":
            return max(S - K, 0.0)
        else:
            return max(K - S, 0.0)

    if sigma <= 0:
        return 0.0

    dt = T / n_steps
    drift = (r - 0.5 * sigma ** 2) * dt
    vol = sigma * np.sqrt(dt)

    # 对偶变量法
    n_half = n_simulations // 2
    Z = np.random.standard_normal((n_half, n_steps))
    Z_anti = -Z

    all_payoffs = []

    for z_set in [Z, Z_anti]:
        log_returns = drift + vol * z_set
        log_prices = np.cumsum(log_returns, axis=1)
        prices = S * np.exp(log_prices)
        prices = np.hstack([np.full((n_half, 1), S), prices])

        ST = prices[:, -1]
        S_max = np.max(prices, axis=1)
        S_min = np.min(prices, axis=1)

        if strike_type == "fixed":
            if option_type == "call":
                payoffs = np.maximum(S_max - K, 0.0)
            else:
                payoffs = np.maximum(K - S_min, 0.0)
        else:  # floating
            if option_type == "call":
                payoffs = np.maximum(ST - S_min, 0.0)
            else:
                payoffs = np.maximum(S_max - ST, 0.0)

        all_payoffs.append(payoffs)

    avg_payoff = (np.mean(all_payoffs[0]) + np.mean(all_payoffs[1])) / 2.0
    price = np.exp(-r * T) * avg_payoff

    return float(max(price, 0.0))
