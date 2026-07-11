"""
期权定价模型统一接口

根据期权类型自动选择对应的定价模型进行估值。
支持的期权类型(19种):
    基础类型:
    - european:       欧式期权 (Black-Scholes-Merton)
    - american:       美式期权 (CRR二叉树)
    - asian:          亚式期权 (蒙特卡洛/解析解)
    - barrier:        障碍期权 (解析近似/蒙特卡洛)
    - lookback:       回望期权 (蒙特卡洛)

    高级奇异期权:
    - binary:         数字期权/二元期权 (cash_or_nothing/asset_or_nothing)
    - chooser:        选择权期权 (在指定日期选择call或put)
    - compound:       复合期权 (期权上的期权)
    - forward_start:  远期生效期权 (在未来某时刻生效)
    - power:          幂期权 (收益基于S^n)
    - exchange:       交换期权 (Margrabe公式)
    - cliquet:        棘轮期权 (多个远期生效期权组合)
    - shout:          喊价期权 (可锁定收益)
    - double_barrier: 双边障碍期权 (上下双障碍)
    - range:          区间期权 (价格是否在区间内)
    - quanto:         数量调整期权 (跨币种)
    - rainbow:        彩虹期权 (多资产最优/最差)
    - spread:         价差期权 (两资产价差)
    - barrier_lookback: 回望障碍期权 (障碍+回望组合)
"""
from pricing.european import black_scholes
from pricing.american import american_option
from pricing.asian import asian_option
from pricing.exotic import barrier_option, lookback_option
from pricing.exotic_advanced import (
    binary_option,
    chooser_option,
    compound_option,
    forward_start_option,
    power_option,
    exchange_option,
    cliquet_option,
    shout_option,
    double_barrier_option,
    range_option,
    quanto_option,
    rainbow_option,
    spread_option,
    barrier_lookback_option,
)
from pricing.greeks import calculate_greeks

# 期权类型中文名映射
OPTION_TYPE_NAMES = {
    # 基础类型
    "european": "欧式期权",
    "american": "美式期权",
    "asian": "亚式期权",
    "barrier": "障碍期权",
    "lookback": "回望期权",
    # 高级奇异期权
    "binary": "数字期权",
    "chooser": "选择权期权",
    "compound": "复合期权",
    "forward_start": "远期生效期权",
    "power": "幂期权",
    "exchange": "交换期权",
    "cliquet": "棘轮期权",
    "shout": "喊价期权",
    "double_barrier": "双边障碍期权",
    "range": "区间期权",
    "quanto": "数量调整期权",
    "rainbow": "彩虹期权",
    "spread": "价差期权",
    "barrier_lookback": "回望障碍期权",
}

# 所有支持的期权类型列表
ALL_OPTION_TYPES = list(OPTION_TYPE_NAMES.keys())


def price_option(
    option_type: str,
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    call_put: str = "call",
    model_params: dict = None,
    **kwargs,
) -> float:
    """
    统一期权定价接口

    参数:
        option_type: 期权类型(见上方19种)
        S: 标的资产当前价格
        K: 行权价
        T: 到期时间(年)
        r: 无风险利率(小数)
        sigma: 年化波动率(小数)
        call_put: "call" 或 "put"
        model_params: RSI优化后的模型参数字典,可选
        **kwargs: 额外参数(因期权类型而异)

    返回:
        期权理论价格
    """
    if T <= 0:
        if call_put == "call":
            return max(S - K, 0.0)
        else:
            return max(K - S, 0.0)

    mp = model_params or {}

    # ============ 基础期权类型 ============

    if option_type == "european":
        return black_scholes(S, K, T, r, sigma, call_put)

    elif option_type == "american":
        steps = mp.get("american_steps", 200)
        return american_option(S, K, T, r, sigma, call_put, steps=steps)

    elif option_type == "asian":
        obs_type = kwargs.get("observation_type", "arithmetic")
        n_sim = mp.get("asian_n_simulations", 20000)
        return asian_option(S, K, T, r, sigma, call_put, observation_type=obs_type,
                           n_simulations=n_sim)

    elif option_type == "barrier":
        H = kwargs.get("barrier_level", S * 1.1)
        bt = kwargs.get("barrier_type", "up_and_out")
        n_sim = mp.get("barrier_n_simulations", 20000)
        return barrier_option(S, K, T, r, sigma, H, bt, call_put,
                             n_simulations=n_sim)

    elif option_type == "lookback":
        st = kwargs.get("strike_type", "fixed")
        n_sim = mp.get("lookback_n_simulations", 20000)
        return lookback_option(S, K, T, r, sigma, call_put, strike_type=st,
                              n_simulations=n_sim)

    # ============ 高级奇异期权 ============

    elif option_type in ("binary", "digital"):
        binary_type = kwargs.get("binary_type", "cash_or_nothing")
        payoff = kwargs.get("payoff", 1.0)
        return binary_option(S, K, T, r, sigma, call_put,
                            binary_type=binary_type, payoff=payoff)

    elif option_type == "chooser":
        choose_time = kwargs.get("choose_time")
        K_put = kwargs.get("K_put")
        n_sim = mp.get("chooser_n_simulations", 20000)
        return chooser_option(S, K, T, r, sigma,
                             choose_time=choose_time, K_put=K_put,
                             n_simulations=n_sim)

    elif option_type == "compound":
        K1 = kwargs.get("K1", K)
        K2 = kwargs.get("K2", K)
        T1 = kwargs.get("T1", T * 0.5)
        T2 = kwargs.get("T2", T)
        compound_type = kwargs.get("compound_type", "call_on_call")
        n_sim = mp.get("compound_n_simulations", 20000)
        return compound_option(S, K1, K2, T1, T2, r, sigma,
                              compound_type=compound_type,
                              n_simulations=n_sim)

    elif option_type == "forward_start":
        start_time = kwargs.get("start_time")
        alpha = kwargs.get("alpha", 1.0)
        return forward_start_option(S, K, T, r, sigma,
                                    start_time=start_time, alpha=alpha,
                                    option_type=call_put)

    elif option_type == "power":
        power = kwargs.get("power", 2.0)
        n_sim = mp.get("power_n_simulations", 20000)
        return power_option(S, K, T, r, sigma, call_put,
                           power=power, n_simulations=n_sim)

    elif option_type == "exchange":
        S1 = kwargs.get("S1", S)
        S2 = kwargs.get("S2", K)
        sigma1 = kwargs.get("sigma1", sigma)
        sigma2 = kwargs.get("sigma2", sigma * 0.8)
        rho = kwargs.get("rho", 0.5)
        return exchange_option(S1, S2, T, r, sigma1, sigma2, rho,
                               option_type=call_put)

    elif option_type == "cliquet":
        n_periods = kwargs.get("n_periods", 4)
        cap = kwargs.get("cap", 0.10)
        floor = kwargs.get("floor", 0.0)
        n_sim = mp.get("cliquet_n_simulations", 20000)
        return cliquet_option(S, K, T, r, sigma,
                             n_periods=n_periods, cap=cap, floor=floor,
                             option_type=call_put, n_simulations=n_sim)

    elif option_type == "shout":
        n_sim = mp.get("shout_n_simulations", 20000)
        n_steps = mp.get("shout_n_steps", 252)
        return shout_option(S, K, T, r, sigma, call_put,
                           n_simulations=n_sim, n_steps=n_steps)

    elif option_type == "double_barrier":
        H_lower = kwargs.get("H_lower", S * 0.8)
        H_upper = kwargs.get("H_upper", S * 1.2)
        bt = kwargs.get("barrier_type", "knock_out")
        n_sim = mp.get("double_barrier_n_simulations", 20000)
        n_steps = mp.get("double_barrier_n_steps", 252)
        return double_barrier_option(S, K, T, r, sigma,
                                     H_lower=H_lower, H_upper=H_upper,
                                     option_type=call_put, barrier_type=bt,
                                     n_simulations=n_sim, n_steps=n_steps)

    elif option_type == "range":
        H_lower = kwargs.get("H_lower", S * 0.8)
        H_upper = kwargs.get("H_upper", S * 1.2)
        payoff = kwargs.get("payoff", 1.0)
        range_type = kwargs.get("range_type", "inside")
        n_sim = mp.get("range_n_simulations", 20000)
        n_steps = mp.get("range_n_steps", 252)
        return range_option(S, T, r, sigma,
                           H_lower=H_lower, H_upper=H_upper,
                           payoff=payoff, range_type=range_type,
                           n_simulations=n_sim, n_steps=n_steps)

    elif option_type == "quanto":
        r_d = kwargs.get("r_d", r)
        r_f = kwargs.get("r_f", 0.01)
        sigma_s = kwargs.get("sigma_s", sigma)
        sigma_fx = kwargs.get("sigma_fx", 0.10)
        rho = kwargs.get("rho", 0.0)
        return quanto_option(S, K, T, r_d, r_f, sigma_s, sigma_fx, rho,
                            option_type=call_put)

    elif option_type == "rainbow":
        S1 = kwargs.get("S1", S)
        S2 = kwargs.get("S2", K)
        sigma1 = kwargs.get("sigma1", sigma)
        sigma2 = kwargs.get("sigma2", sigma * 0.8)
        rho = kwargs.get("rho", 0.5)
        rainbow_type = kwargs.get("rainbow_type", "best_of")
        n_sim = mp.get("rainbow_n_simulations", 20000)
        return rainbow_option(S1, S2, K, T, r, sigma1, sigma2, rho,
                             option_type=call_put, rainbow_type=rainbow_type,
                             n_simulations=n_sim)

    elif option_type == "spread":
        S1 = kwargs.get("S1", S)
        S2 = kwargs.get("S2", K)
        sigma1 = kwargs.get("sigma1", sigma)
        sigma2 = kwargs.get("sigma2", sigma * 0.8)
        rho = kwargs.get("rho", 0.5)
        n_sim = mp.get("spread_n_simulations", 20000)
        return spread_option(S1, S2, K, T, r, sigma1, sigma2, rho,
                            option_type=call_put, n_simulations=n_sim)

    elif option_type == "barrier_lookback":
        H = kwargs.get("barrier_level", S * 1.1)
        bt = kwargs.get("barrier_type", "up_and_out")
        strike_type = kwargs.get("strike_type", "fixed")
        n_sim = mp.get("barrier_lookback_n_simulations", 20000)
        n_steps = mp.get("barrier_lookback_n_steps", 252)
        return barrier_lookback_option(S, K, T, r, sigma,
                                       H=H, barrier_type=bt,
                                       option_type=call_put,
                                       strike_type=strike_type,
                                       n_simulations=n_sim, n_steps=n_steps)

    else:
        raise ValueError(f"不支持的期权类型: {option_type}")


def get_greeks(
    option_type: str,
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    call_put: str = "call",
    full: bool = True,
    **kwargs,
) -> dict:
    """
    统一Greeks计算接口

    参数:
        option_type: 期权类型
        S, K, T, r, sigma: 标准BSM参数
        call_put: "call" 或 "put"
        full: True返回完整14个Greeks, False返回简版5个

    返回:
        full=True: {delta, gamma, vega, theta, rho, vanna, volga, charm, veta, color, zomma, speed, ultima, lambda}
        full=False: {delta, gamma, vega, theta, rho}
    """
    return calculate_greeks(S, K, T, r, sigma, call_put,
                            pricing_model=option_type, full=full, **kwargs)


def get_all_option_types() -> list:
    """获取所有支持的期权类型列表"""
    return ALL_OPTION_TYPES


def get_option_type_name(option_type: str) -> str:
    """获取期权类型的中文名称"""
    return OPTION_TYPE_NAMES.get(option_type, option_type)
