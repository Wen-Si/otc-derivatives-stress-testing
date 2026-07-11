"""
高级奇异期权定价模型

新增期权类型:
1. 数字期权 (Binary/Digital Options): cash_or_nothing, asset_or_nothing
2. 选择权期权 (Chooser Option): 在指定日期选择call或put
3. 复合期权 (Compound Option): 期权上的期权 (Call-on-Call, Put-on-Call等)
4. 远期生效期权 (Forward Start Option): 在未来某时刻生效的期权
5. 幂期权 (Power Option): 收益基于S^n
6. 交换期权 (Exchange Option): 用Margrabe公式定价
7. 棘轮期权 (Cliquet Option): 多个远期生效期权的组合
8. 喊价期权 (Shout Option): 可锁定收益的期权
9. 双边障碍期权 (Double Barrier Option): 上下双障碍
10. 区间期权 (Range/Bet Option): 价格是否在区间内
11. 数量调整期权 (Quanto Option): 跨币种期权
12. 彩虹期权 (Rainbow Option): 多资产最优/最差/差价
13. 价差期权 (Spread Option): 两资产价差
14. 敲出回望期权 (Barrier-Lookback): 障碍+回望组合
"""
import numpy as np
from scipy.stats import norm
from pricing.european import black_scholes


# ============ 1. 数字期权 (Binary/Digital Options) ============

def binary_option(S: float, K: float, T: float, r: float, sigma: float,
                   option_type: str = "call", binary_type: str = "cash_or_nothing",
                   payoff: float = 1.0) -> float:
    """
    数字期权(二元期权)定价

    参数:
        S: 标的当前价格
        K: 行权价
        T: 到期时间(年)
        r: 无风险利率
        sigma: 波动率
        option_type: "call" 或 "put"
        binary_type: "cash_or_nothing"(现金或无) 或 "asset_or_nothing"(资产或无)
        payoff: 现金或无期权的固定支付金额(默认1.0)

    收益:
        - cash_or_nothing call: 到期S>K时支付payoff,否则0
        - cash_or_nothing put: 到期S<K时支付payoff,否则0
        - asset_or_nothing call: 到期S>K时支付S,否则0
        - asset_or_nothing put: 到期S<K时支付S,否则0
    """
    if T <= 0:
        if binary_type == "cash_or_nothing":
            if option_type == "call":
                return payoff if S > K else 0.0
            else:
                return payoff if S < K else 0.0
        else:  # asset_or_nothing
            if option_type == "call":
                return S if S > K else 0.0
            else:
                return S if S < K else 0.0

    if sigma <= 0:
        # 确定性情况
        ST = S * np.exp(r * T)
        if binary_type == "cash_or_nothing":
            if option_type == "call":
                return payoff * np.exp(-r * T) if ST > K else 0.0
            else:
                return payoff * np.exp(-r * T) if ST < K else 0.0
        else:
            if option_type == "call":
                return ST * np.exp(-r * T) if ST > K else 0.0
            else:
                return ST * np.exp(-r * T) if ST < K else 0.0

    d2 = (np.log(S / K) + (r - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))

    if binary_type == "cash_or_nothing":
        if option_type == "call":
            return float(payoff * np.exp(-r * T) * norm.cdf(d2))
        else:
            return float(payoff * np.exp(-r * T) * norm.cdf(-d2))
    else:  # asset_or_nothing
        d1 = d2 + sigma * np.sqrt(T)
        if option_type == "call":
            return float(S * np.exp(-r * T) * np.exp(r * T) * norm.cdf(d1))
        else:
            return float(S * norm.cdf(-d1))


# ============ 2. 选择权期权 (Chooser Option) ============

def chooser_option(S: float, K: float, T: float, r: float, sigma: float,
                   choose_time: float = None, K_put: float = None,
                   n_simulations: int = 20000) -> float:
    """
    选择权期权定价

    在choose_time时刻,持有者可以选择将期权变为call或put。
    到期时T时刻行权。

    参数:
        S: 标的当前价格
        K: call行权价
        T: 到期时间(年)
        r: 无风险利率
        sigma: 波动率
        choose_time: 选择时间(年),默认T/2
        K_put: put行权价(默认等于K * exp(r*(T-choose_time))以保持put-call parity)

    解析公式:
        Chooser = Call(t1, T, K) + Put(t1, T, K_put)
        其中t1 = choose_time
    """
    if T <= 0:
        return max(S - K, 0.0)

    if choose_time is None:
        choose_time = T / 2.0

    if choose_time >= T:
        choose_time = T * 0.99

    if K_put is None:
        # 保持平价: K_put = K * exp(r*(T-choose_time))
        K_put = K * np.exp(r * (T - choose_time))

    # 解析解: Chooser = Call(choose_time, T, K) + Put(choose_time, T, K_put)
    # 在choose_time时刻,call的价值 = BSM call on S_choose with K, T-t1
    # put的价值 = BSM put on S_choose with K_put, T-t1
    # 使用Rubinstein公式:
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    d1_p = (np.log(S / K_put) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2_p = d1_p - sigma * np.sqrt(T)

    # Call部分
    call_part = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    # Put部分
    put_part = K_put * np.exp(-r * T) * norm.cdf(-d2_p) - S * norm.cdf(-d1_p)

    return float(max(call_part + put_part, 0.0))


# ============ 3. 复合期权 (Compound Option) ============

def compound_option(S: float, K1: float, K2: float, T1: float, T2: float,
                     r: float, sigma: float, compound_type: str = "call_on_call",
                     n_simulations: int = 20000) -> float:
    """
    复合期权定价 - 期权上的期权

    参数:
        S: 标的当前价格
        K1: 复合期权的行权价(在T1时刻支付以获得标的期权)
        K2: 标的期权的行权价(在T2时刻)
        T1: 复合期权到期时间(年)
        T2: 标的期权到期时间(年) T2 > T1
        r: 无风险利率
        sigma: 波动率
        compound_type: "call_on_call"/"put_on_call"/"call_on_put"/"put_on_put"

    解析公式(Geske 1979):
        使用二维正态分布计算复合期权价值
    """
    if T1 <= 0:
        # 复合期权到期,评估标的期权价值
        remaining_T = T2 - T1
        if remaining_T <= 0:
            underlying_val = max(S - K2, 0.0) if "call" in compound_type.split("_")[2] else max(K2 - S, 0.0)
        else:
            underlying_type = "call" if "call" in compound_type.split("_")[2] else "put"
            underlying_val = black_scholes(S, K2, remaining_T, r, sigma, underlying_type)

        if "call" in compound_type.split("_")[0]:
            return max(underlying_val - K1, 0.0)
        else:
            return max(K1 - underlying_val, 0.0)

    if T2 <= T1:
        T2 = T1 + 0.001

    # 计算临界价格S* (使得在T1时刻标的期权价值=K1)
    underlying_type = "call" if "call" in compound_type.split("_")[2] else "put"

    # 使用牛顿迭代法求解S*
    S_star = S  # 初始猜测
    for _ in range(50):
        bs_val = black_scholes(S_star, K2, T2 - T1, r, sigma, underlying_type)
        d_bs = _bs_delta(S_star, K2, T2 - T1, r, sigma, underlying_type)
        if abs(d_bs) < 1e-10:
            break
        S_star = S_star - (bs_val - K1) / d_bs
        if S_star <= 0:
            S_star = 0.01
            break

    # 计算复合期权价值
    d1 = (np.log(S / S_star) + (r + 0.5 * sigma ** 2) * T1) / (sigma * np.sqrt(T1))
    d2 = d1 - sigma * np.sqrt(T1)

    bs_d1 = (np.log(S / K2) + (r + 0.5 * sigma ** 2) * T2) / (sigma * np.sqrt(T2))
    bs_d2 = bs_d1 - sigma * np.sqrt(T2)

    # 二维正态分布累积函数
    rho = np.sqrt(T1 / T2)

    from scipy.stats import multivariate_normal
    mvn = multivariate_normal(mean=[0, 0], cov=[[1, rho], [rho, 1]])

    a1 = bs_d1  # 标的期权d1
    a2 = bs_d2  # 标的期权d2
    b1 = d1     # 复合期权d1
    b2 = d2     # 复合期权d2

    if compound_type == "call_on_call":
        M1 = mvn.cdf([a1, b1])
        M2 = mvn.cdf([a2, b2])
        price = S * M1 - K2 * np.exp(-r * T2) * M2 - K1 * np.exp(-r * T1) * norm.cdf(b1)
    elif compound_type == "put_on_call":
        M1 = mvn.cdf([-a1, -b1])
        M2 = mvn.cdf([-a2, -b2])
        price = K1 * np.exp(-r * T1) * norm.cdf(-b1) - S * M1 + K2 * np.exp(-r * T2) * M2
    elif compound_type == "call_on_put":
        M1 = mvn.cdf([-a1, b1])
        M2 = mvn.cdf([-a2, b2])
        price = K2 * np.exp(-r * T2) * M2 - S * M1 - K1 * np.exp(-r * T1) * norm.cdf(b1)
    elif compound_type == "put_on_put":
        M1 = mvn.cdf([a1, -b1])
        M2 = mvn.cdf([a2, -b2])
        price = K1 * np.exp(-r * T1) * norm.cdf(-b1) - K2 * np.exp(-r * T2) * M2 + S * M1
    else:
        price = 0.0

    return float(max(price, 0.0))


def _bs_delta(S: float, K: float, T: float, r: float, sigma: float,
              option_type: str = "call") -> float:
    """BSM Delta"""
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    if option_type == "call":
        return norm.cdf(d1)
    else:
        return norm.cdf(d1) - 1


# ============ 4. 远期生效期权 (Forward Start Option) ============

def forward_start_option(S: float, K: float, T: float, r: float, sigma: float,
                         start_time: float = None, alpha: float = 1.0,
                         option_type: str = "call") -> float:
    """
    远期生效期权定价

    期权在start_time时刻生效,行权价设为 alpha * S_start。
    到期时间 = T - start_time

    参数:
        S: 标的当前价格
        K: 此参数忽略(行权价由alpha决定),保留用于接口统一
        T: 总期限(年)
        r: 无风险利率
        sigma: 波动率
        start_time: 期权生效时间(年),默认T/2
        alpha: 行权价系数, K_start = alpha * S_start
        option_type: "call" 或 "put"

    解析公式:
        V = S * [call_on_forward(1, alpha, T-t1, r, sigma)]
        即: 当前价值 = 当前价格 * 远期生效的BSM期权价值(以S=1标准化)
    """
    if T <= 0:
        return 0.0

    if start_time is None:
        start_time = T / 2.0

    if start_time >= T:
        start_time = T * 0.99

    tau = T - start_time  # 期权有效期

    if tau <= 0 or sigma <= 0:
        return 0.0

    # 标准化BSM (S=1, K=alpha)
    d1 = (np.log(1.0 / alpha) + (r + 0.5 * sigma ** 2) * tau) / (sigma * np.sqrt(tau))
    d2 = d1 - sigma * np.sqrt(tau)

    if option_type == "call":
        bs_val = norm.cdf(d1) - alpha * np.exp(-r * tau) * norm.cdf(d2)
    else:
        bs_val = alpha * np.exp(-r * tau) * norm.cdf(-d2) - norm.cdf(-d1)

    # 远期生效期权的价值
    price = S * np.exp(-r * start_time) * bs_val

    return float(max(price, 0.0))


# ============ 5. 幂期权 (Power Option) ============

def power_option(S: float, K: float, T: float, r: float, sigma: float,
                 option_type: str = "call", power: float = 2.0,
                 n_simulations: int = 20000) -> float:
    """
    幂期权定价

    收益基于标的价格的n次幂: max(S_T^n - K, 0) for call

    参数:
        S: 标的当前价格
        K: 行权价
        T: 到期时间(年)
        r: 无风险利率
        sigma: 波动率
        option_type: "call" 或 "put"
        power: 幂指数n(默认2.0)

    对于power=2,存在解析公式(Jarrow-Rudd 1981):
        Call = S^n * exp((n-1)(r + n*sigma^2/2) * T) - K * exp(-rT) * N(d2)
    一般情况使用蒙特卡洛
    """
    n = power

    if T <= 0:
        if option_type == "call":
            return max(S ** n - K, 0.0)
        else:
            return max(K - S ** n, 0.0)

    if sigma <= 0:
        ST = S * np.exp(r * T)
        if option_type == "call":
            return max(ST ** n - K, 0.0) * np.exp(-r * T)
        else:
            return max(K - ST ** n, 0.0) * np.exp(-r * T)

    # 解析解适用于幂期权
    # 对于S^n的期望: E[S_T^n] = S^n * exp(n*r*T + 0.5*n*(n-1)*sigma^2*T)
    drift_n = n * r + 0.5 * n * (n - 1) * sigma ** 2
    sigma_n = n * sigma

    d1 = (np.log(S ** n / K) + (drift_n + 0.5 * sigma_n ** 2) * T) / (sigma_n * np.sqrt(T))
    d2 = d1 - sigma_n * np.sqrt(T)

    if option_type == "call":
        price = (S ** n) * np.exp((drift_n - r) * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - (S ** n) * np.exp((drift_n - r) * T) * norm.cdf(-d1)

    return float(max(price, 0.0))


# ============ 6. 交换期权 (Exchange Option) ============

def exchange_option(S1: float, S2: float, T: float, r: float,
                    sigma1: float, sigma2: float, rho: float = 0.5,
                    option_type: str = "call") -> float:
    """
    交换期权定价 (Margrabe 1978)

    收益: max(S1_T - S2_T, 0) for call (用S2交换S1)
          max(S2_T - S1_T, 0) for put (用S1交换S2)

    参数:
        S1: 资产1当前价格(被交换获得的)
        S2: 资产2当前价格(交换出去的)
        T: 到期时间(年)
        r: 无风险利率
        sigma1: 资产1波动率
        sigma2: 资产2波动率
        rho: 两资产相关系数
        option_type: "call"(获得S1) 或 "put"(获得S2)

    Margrabe公式:
        Call = S1 * N(d1) - S2 * N(d2)
        其中 sigma_hat = sqrt(sigma1^2 + sigma2^2 - 2*rho*sigma1*sigma2)
    """
    if T <= 0:
        if option_type == "call":
            return max(S1 - S2, 0.0)
        else:
            return max(S2 - S1, 0.0)

    sigma_hat = np.sqrt(sigma1 ** 2 + sigma2 ** 2 - 2 * rho * sigma1 * sigma2)

    if sigma_hat <= 1e-10:
        return 0.0

    d1 = (np.log(S1 / S2) + 0.5 * sigma_hat ** 2 * T) / (sigma_hat * np.sqrt(T))
    d2 = d1 - sigma_hat * np.sqrt(T)

    if option_type == "call":
        price = S1 * norm.cdf(d1) - S2 * norm.cdf(d2)
    else:
        price = S2 * norm.cdf(-d2) - S1 * norm.cdf(-d1)

    return float(max(price, 0.0))


# ============ 7. 棘轮期权 (Cliquet Option) ============

def cliquet_option(S: float, K: float, T: float, r: float, sigma: float,
                   n_periods: int = 4, cap: float = 0.10, floor: float = 0.0,
                   option_type: str = "call",
                   n_simulations: int = 20000) -> float:
    """
    棘轮期权(Cliquet/Forward-Start Chain)定价

    由多个远期生效期权组成,每期收益有上限(cap)和下限(floor)。
    总收益为各期收益之和。

    参数:
        S: 标的当前价格
        K: 初始行权价(通常=S或K=S)
        T: 总期限(年)
        r: 无风险利率
        sigma: 波动率
        n_periods: 期数(将T等分)
        cap: 每期收益率上限
        floor: 每期收益率下限
        option_type: "call" 或 "put"

    每期收益: max(R_i, floor) but capped at cap, 其中R_i = S_i/S_{i-1} - 1
    """
    if T <= 0:
        return 0.0

    dt = T / n_periods
    # 每期等价于一个远期生效期权,行权价为S_start*(1+floor)
    # 实际上棘轮期权的解析定价较复杂,这里使用蒙特卡洛

    n_half = n_simulations // 2
    Z = np.random.standard_normal((n_half, n_periods))
    Z_anti = -Z

    all_payoffs = []

    for z_set in [Z, Z_anti]:
        prices = np.zeros((n_half, n_periods + 1))
        prices[:, 0] = S
        for j in range(n_periods):
            prices[:, j + 1] = prices[:, j] * np.exp((r - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * z_set[:, j])

        # 每期收益率
        returns = prices[:, 1:] / prices[:, :-1] - 1.0

        if option_type == "call":
            period_payoffs = np.maximum(returns, floor)
        else:
            period_payoffs = np.maximum(-returns, floor)

        # 应用上限
        period_payoffs = np.minimum(period_payoffs, cap)

        total_payoff = np.sum(period_payoffs, axis=1)
        all_payoffs.append(total_payoff)

    avg_payoff = (np.mean(all_payoffs[0]) + np.mean(all_payoffs[1])) / 2.0
    price = np.exp(-r * T) * avg_payoff * S

    return float(max(price, 0.0))


# ============ 8. 喊价期权 (Shout Option) ============

def shout_option(S: float, K: float, T: float, r: float, sigma: float,
                 option_type: str = "call",
                 n_simulations: int = 20000, n_steps: int = 252) -> float:
    """
    喊价期权定价

    持有者可以在期权有效期内"喊价"一次,锁定当时的内在收益。
    到期收益 = max(喊价收益, 到期收益)。

    参数:
        S: 标的当前价格
        K: 行权价
        T: 到期时间(年)
        r: 无风险利率
        sigma: 波动率
        option_type: "call" 或 "put"

    使用蒙特卡洛模拟,在每个时间步检查是否喊价最优。
    """
    if T <= 0:
        if option_type == "call":
            return max(S - K, 0.0)
        else:
            return max(K - S, 0.0)

    if sigma <= 0:
        if option_type == "call":
            return max(S * np.exp(r * T) - K, 0.0) * np.exp(-r * T)
        else:
            return max(K - S * np.exp(r * T), 0.0) * np.exp(-r * T)

    dt = T / n_steps
    drift = (r - 0.5 * sigma ** 2) * dt
    vol = sigma * np.sqrt(dt)

    n_half = n_simulations // 2
    Z = np.random.standard_normal((n_half, n_steps))
    Z_anti = -Z

    all_payoffs = []

    for z_set in [Z, Z_anti]:
        log_returns = drift + vol * z_set
        log_prices = np.cumsum(log_returns, axis=1)
        prices = S * np.exp(log_prices)
        prices = np.hstack([np.full((n_half, 1), S), prices])

        # 在每个时间步计算喊价后的收益
        # 喊价收益 = max(intrinsic_at_shout, 0) * exp(-r*(T-t_shout))
        # 到期收益 = max(intrinsic_at_T, 0)

        ST = prices[:, -1]
        if option_type == "call":
            intrinsic_T = np.maximum(ST - K, 0.0)
        else:
            intrinsic_T = np.maximum(K - ST, 0.0)

        # 对每条路径,找到最优喊价时点
        # 简化:使用回望方法,找最大喊价收益
        discount_factors = np.exp(-r * np.linspace(dt, T, n_steps))

        # 每个时间步的喊价收益(折现到期初)
        shout_values = np.zeros((n_half, n_steps))
        for j in range(n_steps):
            S_j = prices[:, j + 1]
            if option_type == "call":
                intrinsic_j = np.maximum(S_j - K, 0.0)
            else:
                intrinsic_j = np.maximum(K - S_j, 0.0)
            shout_values[:, j] = intrinsic_j * discount_factors[j]

        # 最优喊价收益 = max over time of shout_values
        best_shout = np.max(shout_values, axis=1)

        # 最终收益 = max(喊价收益, 到期收益折现)
        payoff_T_discounted = intrinsic_T * np.exp(-r * T)
        final_payoff = np.maximum(best_shout, payoff_T_discounted)

        all_payoffs.append(final_payoff)

    avg_payoff = (np.mean(all_payoffs[0]) + np.mean(all_payoffs[1])) / 2.0
    price = avg_payoff  # 已经折现

    return float(max(price, 0.0))


# ============ 9. 双边障碍期权 (Double Barrier Option) ============

def double_barrier_option(S: float, K: float, T: float, r: float, sigma: float,
                          H_lower: float, H_upper: float,
                          option_type: str = "call", barrier_type: str = "knock_out",
                          n_simulations: int = 20000, n_steps: int = 252) -> float:
    """
    双边障碍期权定价

    有两个障碍水平(上限和下限),价格触碰任一障碍则:
    - knock_out: 期权失效
    - knock_in: 期权生效

    参数:
        S: 标的当前价格
        K: 行权价
        T: 到期时间(年)
        r: 无风险利率
        sigma: 波动率
        H_lower: 下障碍水平
        H_upper: 上障碍水平
        option_type: "call" 或 "put"
        barrier_type: "knock_out" 或 "knock_in"
    """
    if T <= 0:
        if option_type == "call":
            return max(S - K, 0.0)
        else:
            return max(K - S, 0.0)

    # 确保S在障碍之间
    if S >= H_upper or S <= H_lower:
        if barrier_type == "knock_out":
            return 0.0
        else:
            # knock_in已触发
            return black_scholes(S, K, T, r, sigma, option_type)

    dt = T / n_steps
    drift = (r - 0.5 * sigma ** 2) * dt
    vol = sigma * np.sqrt(dt)

    n_half = n_simulations // 2
    Z = np.random.standard_normal((n_half, n_steps))
    Z_anti = -Z

    all_payoffs = []

    for z_set in [Z, Z_anti]:
        log_returns = drift + vol * z_set
        log_prices = np.cumsum(log_returns, axis=1)
        prices = S * np.exp(log_prices)
        prices = np.hstack([np.full((n_half, 1), S), prices])

        # 检查是否触碰任一障碍
        touched_upper = np.max(prices, axis=1) >= H_upper
        touched_lower = np.min(prices, axis=1) <= H_lower
        touched = touched_upper | touched_lower

        ST = prices[:, -1]

        if option_type == "call":
            intrinsic = np.maximum(ST - K, 0.0)
        else:
            intrinsic = np.maximum(K - ST, 0.0)

        if barrier_type == "knock_out":
            payoffs = np.where(touched, 0.0, intrinsic)
        else:  # knock_in
            payoffs = np.where(touched, intrinsic, 0.0)

        all_payoffs.append(payoffs)

    avg_payoff = (np.mean(all_payoffs[0]) + np.mean(all_payoffs[1])) / 2.0
    price = np.exp(-r * T) * avg_payoff

    return float(max(price, 0.0))


# ============ 10. 区间期权 (Range/Bet Option) ============

def range_option(S: float, T: float, r: float, sigma: float,
                 H_lower: float, H_upper: float, payoff: float = 1.0,
                 range_type: str = "inside",
                 n_simulations: int = 20000, n_steps: int = 252) -> float:
    """
    区间期权(双边触碰/非触碰)定价

    参数:
        S: 标的当前价格
        T: 到期时间(年)
        r: 无风险利率
        sigma: 波动率
        H_lower: 区间下限
        H_upper: 区间上限
        payoff: 固定支付金额
        range_type: "inside"(触碰区间内支付) 或 "outside"(不触碰支付)

    收益:
        - inside: 全程价格在[H_lower, H_upper]内则支付payoff
        - outside: 全程价格触碰区间外则支付payoff
    """
    if T <= 0:
        in_range = H_lower <= S <= H_upper
        if range_type == "inside":
            return payoff if in_range else 0.0
        else:
            return payoff if not in_range else 0.0

    if S >= H_upper or S <= H_lower:
        if range_type == "inside":
            return 0.0
        else:
            return float(payoff * np.exp(-r * T))

    dt = T / n_steps
    drift = (r - 0.5 * sigma ** 2) * dt
    vol = sigma * np.sqrt(dt)

    n_half = n_simulations // 2
    Z = np.random.standard_normal((n_half, n_steps))
    Z_anti = -Z

    all_payoffs = []

    for z_set in [Z, Z_anti]:
        log_returns = drift + vol * z_set
        log_prices = np.cumsum(log_returns, axis=1)
        prices = S * np.exp(log_prices)
        prices = np.hstack([np.full((n_half, 1), S), prices])

        touched_upper = np.max(prices, axis=1) >= H_upper
        touched_lower = np.min(prices, axis=1) <= H_lower
        touched = touched_upper | touched_lower
        stayed_in = ~touched

        if range_type == "inside":
            payoffs = np.where(stayed_in, payoff, 0.0)
        else:  # outside
            payoffs = np.where(touched, payoff, 0.0)

        all_payoffs.append(payoffs)

    avg_payoff = (np.mean(all_payoffs[0]) + np.mean(all_payoffs[1])) / 2.0
    price = np.exp(-r * T) * avg_payoff

    return float(max(price, 0.0))


# ============ 11. 数量调整期权 (Quanto Option) ============

def quanto_option(S: float, K: float, T: float, r_d: float, r_f: float,
                  sigma_s: float, sigma_fx: float, rho: float = 0.0,
                  option_type: str = "call") -> float:
    """
    数量调整期权(Quanto)定价

    标的资产以外币计价,期权以本币结算。
    Quanto调整后的漂移率为: r_d - r_f - rho * sigma_s * sigma_fx

    参数:
        S: 标的资产价格(外币计价)
        K: 行权价(外币计价)
        T: 到期时间(年)
        r_d: 本币无风险利率(国内利率)
        r_f: 外币无风险利率(外国利率)
        sigma_s: 标的资产波动率
        sigma_fx: 汇率波动率
        rho: 标的与汇率的相关系数
        option_type: "call" 或 "put"
    """
    if T <= 0:
        if option_type == "call":
            return max(S - K, 0.0)
        else:
            return max(K - S, 0.0)

    # Quanto调整后的漂移率
    mu_q = r_d - r_f - rho * sigma_s * sigma_fx

    d1 = (np.log(S / K) + (mu_q + 0.5 * sigma_s ** 2) * T) / (sigma_s * np.sqrt(T))
    d2 = d1 - sigma_s * np.sqrt(T)

    if option_type == "call":
        price = S * np.exp((mu_q - r_d) * T) * norm.cdf(d1) - K * np.exp(-r_d * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r_d * T) * norm.cdf(-d2) - S * np.exp((mu_q - r_d) * T) * norm.cdf(-d1)

    return float(max(price, 0.0))


# ============ 12. 彩虹期权 (Rainbow Option) ============

def rainbow_option(S1: float, S2: float, K: float, T: float, r: float,
                   sigma1: float, sigma2: float, rho: float = 0.5,
                   option_type: str = "call", rainbow_type: str = "best_of",
                   n_simulations: int = 20000) -> float:
    """
    彩虹期权定价

    参数:
        S1: 资产1当前价格
        S2: 资产2当前价格
        K: 行权价
        T: 到期时间(年)
        r: 无风险利率
        sigma1: 资产1波动率
        sigma2: 资产2波动率
        rho: 相关系数
        option_type: "call" 或 "put"
        rainbow_type:
            "best_of": max(S1_T, S2_T)的期权
            "worst_of": min(S1_T, S2_T)的期权
            "spread": (S1_T - S2_T)的期权
            "max_call": max(max(S1_T,S2_T)-K, 0)

    收益:
        - best_of call: max(max(S1_T, S2_T) - K, 0)
        - worst_of call: max(min(S1_T, S2_T) - K, 0)
        - spread call: max(S1_T - S2_T - K, 0)
        - max_call: max(S1_T, S2_T, K) - K (always positive part)
    """
    if T <= 0:
        if rainbow_type == "best_of":
            val = max(S1, S2)
        elif rainbow_type == "worst_of":
            val = min(S1, S2)
        elif rainbow_type == "spread":
            val = S1 - S2
        else:
            val = max(S1, S2)
        if option_type == "call":
            return max(val - K, 0.0)
        else:
            return max(K - val, 0.0)

    dt = T
    drift1 = (r - 0.5 * sigma1 ** 2) * dt
    drift2 = (r - 0.5 * sigma2 ** 2) * dt
    vol1 = sigma1 * np.sqrt(dt)
    vol2 = sigma2 * np.sqrt(dt)

    # 生成相关随机数
    n_half = n_simulations // 2
    Z1 = np.random.standard_normal(n_half)
    Z2 = rho * Z1 + np.sqrt(1 - rho ** 2) * np.random.standard_normal(n_half)
    Z1_anti = -Z1
    Z2_anti = -Z2

    all_payoffs = []

    for z1, z2 in [(Z1, Z2), (Z1_anti, Z2_anti)]:
        S1_T = S1 * np.exp(drift1 + vol1 * z1)
        S2_T = S2 * np.exp(drift2 + vol2 * z2)

        if rainbow_type == "best_of":
            val = np.maximum(S1_T, S2_T)
        elif rainbow_type == "worst_of":
            val = np.minimum(S1_T, S2_T)
        elif rainbow_type == "spread":
            val = S1_T - S2_T
        else:  # max_call
            val = np.maximum(S1_T, S2_T)

        if option_type == "call":
            payoffs = np.maximum(val - K, 0.0)
        else:
            payoffs = np.maximum(K - val, 0.0)

        all_payoffs.append(payoffs)

    avg_payoff = (np.mean(all_payoffs[0]) + np.mean(all_payoffs[1])) / 2.0
    price = np.exp(-r * T) * avg_payoff

    return float(max(price, 0.0))


# ============ 13. 价差期权 (Spread Option) ============

def spread_option(S1: float, S2: float, K: float, T: float, r: float,
                  sigma1: float, sigma2: float, rho: float = 0.5,
                  option_type: str = "call",
                  n_simulations: int = 20000) -> float:
    """
    价差期权定价

    收益基于两资产价差: max(S1_T - S2_T - K, 0) for call

    参数:
        S1: 资产1价格(多头)
        S2: 资产2价格(空头)
        K: 价差行权价
        T: 到期时间(年)
        r: 无风险利率
        sigma1: 资产1波动率
        sigma2: 资产2波动率
        rho: 相关系数
        option_type: "call" 或 "put"

    使用蒙特卡洛定价(也称为Kirk近似)
    """
    if T <= 0:
        spread = S1 - S2
        if option_type == "call":
            return max(spread - K, 0.0)
        else:
            return max(K - spread, 0.0)

    # Kirk近似公式(当K=0时退化为Margrabe)
    if abs(K) < 1e-10:
        return exchange_option(S1, S2, T, r, sigma1, sigma2, rho, option_type)

    # Kirk近似
    F = S1 * np.exp(r * T) - S2 * np.exp(r * T) - K
    if F <= 0 and option_type == "call":
        # 价差为负,call可能仍有价值
        pass

    # 蒙特卡洛方法
    dt = T
    drift1 = (r - 0.5 * sigma1 ** 2) * dt
    drift2 = (r - 0.5 * sigma2 ** 2) * dt
    vol1 = sigma1 * np.sqrt(dt)
    vol2 = sigma2 * np.sqrt(dt)

    n_half = n_simulations // 2
    Z1 = np.random.standard_normal(n_half)
    Z2 = rho * Z1 + np.sqrt(1 - rho ** 2) * np.random.standard_normal(n_half)
    Z1_anti = -Z1
    Z2_anti = -Z2

    all_payoffs = []

    for z1, z2 in [(Z1, Z2), (Z1_anti, Z2_anti)]:
        S1_T = S1 * np.exp(drift1 + vol1 * z1)
        S2_T = S2 * np.exp(drift2 + vol2 * z2)

        spread = S1_T - S2_T

        if option_type == "call":
            payoffs = np.maximum(spread - K, 0.0)
        else:
            payoffs = np.maximum(K - spread, 0.0)

        all_payoffs.append(payoffs)

    avg_payoff = (np.mean(all_payoffs[0]) + np.mean(all_payoffs[1])) / 2.0
    price = np.exp(-r * T) * avg_payoff

    return float(max(price, 0.0))


# ============ 14. 回望障碍期权 (Barrier-Lookback) ============

def barrier_lookback_option(S: float, K: float, T: float, r: float, sigma: float,
                             H: float, barrier_type: str = "up_and_out",
                             option_type: str = "call", strike_type: str = "fixed",
                             n_simulations: int = 20000, n_steps: int = 252) -> float:
    """
    回望障碍期权 - 障碍+回望组合

    如果障碍未触碰,则按回望期权结算;
    如果障碍触碰(敲出),则期权失效。

    参数:
        S: 标的当前价格
        K: 行权价(fixed类型使用)
        T: 到期时间(年)
        r: 无风险利率
        sigma: 波动率
        H: 障碍水平
        barrier_type: "up_and_out"/"down_and_out"(仅支持敲出)
        option_type: "call" 或 "put"
        strike_type: "fixed" 或 "floating"
    """
    if T <= 0:
        if option_type == "call":
            return max(S - K, 0.0)
        else:
            return max(K - S, 0.0)

    dt = T / n_steps
    drift = (r - 0.5 * sigma ** 2) * dt
    vol = sigma * np.sqrt(dt)

    n_half = n_simulations // 2
    Z = np.random.standard_normal((n_half, n_steps))
    Z_anti = -Z

    all_payoffs = []

    for z_set in [Z, Z_anti]:
        log_returns = drift + vol * z_set
        log_prices = np.cumsum(log_returns, axis=1)
        prices = S * np.exp(log_prices)
        prices = np.hstack([np.full((n_half, 1), S), prices])

        # 检查障碍
        if "up" in barrier_type:
            touched = np.max(prices, axis=1) >= H
        else:
            touched = np.min(prices, axis=1) <= H

        ST = prices[:, -1]
        S_max = np.max(prices, axis=1)
        S_min = np.min(prices, axis=1)

        # 回望期权收益
        if strike_type == "fixed":
            if option_type == "call":
                lookback_payoff = np.maximum(S_max - K, 0.0)
            else:
                lookback_payoff = np.maximum(K - S_min, 0.0)
        else:  # floating
            if option_type == "call":
                lookback_payoff = np.maximum(ST - S_min, 0.0)
            else:
                lookback_payoff = np.maximum(S_max - ST, 0.0)

        # 敲出: 触碰则收益为0
        payoffs = np.where(touched, 0.0, lookback_payoff)

        all_payoffs.append(payoffs)

    avg_payoff = (np.mean(all_payoffs[0]) + np.mean(all_payoffs[1])) / 2.0
    price = np.exp(-r * T) * avg_payoff

    return float(max(price, 0.0))
