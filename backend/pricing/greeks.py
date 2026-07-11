"""
期权希腊字母(Greeks)计算 - 完整版

包含标准希腊字母、二阶交叉希腊字母、三阶希腊字母:

标准一阶/二阶:
    - Delta:  dV/dS    标的价格敏感度
    - Gamma:  d2V/dS2  Delta的变化率
    - Vega:   dV/dσ    波动率敏感度
    - Theta:  dV/dt    时间衰减
    - Rho:    dV/dr    利率敏感度

二阶交叉(Cross Greeks):
    - Vanna:  dDelta/dσ = dVega/dS    Delta对波动率的敏感度
    - Volga/Vomma: d2V/dσ2            Vega对波动率的变化率
    - Charm:  dDelta/dt                Delta的时间衰减
    - Veta:   dVega/dt                 Vega的时间衰减
    - Color:  dGamma/dt                Gamma的时间衰减
    - Zomma:  dGamma/dσ                Gamma对波动率的敏感度

三阶:
    - Speed:  d3V/dS3 = dGamma/dS      Gamma对标的价格的变化率
    - Ultima: d3V/dσ3 = dVolga/dσ      Volga对波动率的变化率

其他:
    - Lambda: Ω = dV/dS * S/V         弹性(杠杆率)
"""
import numpy as np
from scipy.stats import norm
from pricing.european import black_scholes


# ============ BSM解析Greeks ============

def _bsm_greeks_full(S: float, K: float, T: float, r: float, sigma: float,
                     option_type: str = "call") -> dict:
    """欧式期权BSM完整Greeks解析解"""
    if T <= 0 or sigma <= 0:
        return _zero_greeks()

    sqrt_T = np.sqrt(T)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    N_d1 = norm.cdf(d1)
    N_d2 = norm.cdf(d2)
    n_d1 = norm.pdf(d1)  # phi(d1)

    if option_type == "call":
        delta = N_d1
        rho_val = K * T * np.exp(-r * T) * N_d2
        theta_val = (-S * n_d1 * sigma / (2 * sqrt_T)
                     - r * K * np.exp(-r * T) * N_d2)
    else:
        delta = N_d1 - 1
        rho_val = -K * T * np.exp(-r * T) * norm.cdf(-d2)
        theta_val = (-S * n_d1 * sigma / (2 * sqrt_T)
                     + r * K * np.exp(-r * T) * norm.cdf(-d2))

    gamma = n_d1 / (S * sigma * sqrt_T)
    vega_raw = S * n_d1 * sqrt_T

    # ============ 二阶交叉 Greeks ============

    # Vanna = dDelta/dsigma = dVega/dS
    # Vanna = -phi(d1) * d2/sigma  (for BSM)
    vanna = -n_d1 * d2 / sigma

    # Volga/Vomma = d2V/dsigma2 = dVega/dsigma
    # Volga = vega * d1 * d2 / sigma
    volga = vega_raw * d1 * d2 / sigma

    # Charm = dDelta/dt (delta decay per day)
    # Charm = -n_d1 * (2*r*T - d2*sigma*sqrt_T) / (2*T*sigma*sqrt_T)
    charm = -n_d1 * (2 * r * T - d2 * sigma * sqrt_T) / (2 * T * sigma * sqrt_T)

    # Veta = dVega/dt (vega decay per day)
    # Veta = S * n_d1 * sqrt_T * [r - (d1*sigma)/(2*sqrt_T) + (1-d1*d2)/(2*T)]
    veta = vega_raw * (r - (d1 * sigma) / (2 * sqrt_T) + (1 - d1 * d2) / (2 * T))

    # Color = dGamma/dt (gamma decay per day)
    # Color = -n_d1 / (2*S*sigma*T^1.5) * [1 + (2*(r*T - d1*sigma*sqrt_T))/(sigma*sqrt_T) + d1*d2/T]
    color = (-n_d1 / (2 * S * sigma * T * sqrt_T) *
             (1 + (2 * (r * T - d1 * sigma * sqrt_T)) / (sigma * sqrt_T) + d1 * d2 / T))

    # Zomma = dGamma/dsigma
    # Zomma = gamma * (d1*d2 - 1) / sigma
    zomma = gamma * (d1 * d2 - 1) / sigma

    # ============ 三阶 Greeks ============

    # Speed = d3V/dS3 = dGamma/dS
    # Speed = -gamma/S * (d1/(sigma*sqrt_T) + 1)
    speed = -gamma / S * (d1 / (sigma * sqrt_T) + 1)

    # Ultima = d3V/dsigma3 = dVolga/dsigma
    # Ultima = -vega / sigma^2 * [d1*d2*(d1*d2 - 1) + d1^2 + d2^2]
    ultima = -vega_raw / (sigma ** 2) * (d1 * d2 * (d1 * d2 - 1) + d1 ** 2 + d2 ** 2)

    # Lambda (elasticity) = Delta * S / Price
    price = black_scholes(S, K, T, r, sigma, option_type)
    lam = delta * S / price if abs(price) > 1e-10 else 0.0

    return {
        # 一阶
        "delta": float(delta),
        "vega": float(vega_raw / 100),
        "theta": float(theta_val / 365),
        "rho": float(rho_val / 100),
        # 二阶
        "gamma": float(gamma),
        "vanna": float(vanna / 100),
        "volga": float(volga / 100),
        "charm": float(charm / 365),
        "veta": float(veta / 365),
        "color": float(color / 365),
        "zomma": float(zomma / 100),
        # 三阶
        "speed": float(speed),
        "ultima": float(ultima / 10000),
        # 其他
        "lambda": float(lam),
    }


def _zero_greeks() -> dict:
    """返回所有Greeks为零的字典"""
    return {
        "delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0, "rho": 0.0,
        "vanna": 0.0, "volga": 0.0, "charm": 0.0, "veta": 0.0, "color": 0.0, "zomma": 0.0,
        "speed": 0.0, "ultima": 0.0, "lambda": 0.0,
    }


# ============ 有限差分法Greeks(适用于所有期权类型) ============

def _finite_difference_greeks_full(pricing_func, S: float, K: float, T: float, r: float, sigma: float,
                                    option_type: str = "call", **kwargs) -> dict:
    """
    有限差分法计算完整Greeks

    使用中心差分法和三点公式:
        一阶导: f'(x) ≈ [f(x+h) - f(x-h)] / (2h)
        二阶导: f''(x) ≈ [f(x+h) - 2f(x) + f(x-h)] / h^2
        三阶导: f'''(x) ≈ [f(x+2h) - 2f(x+h) + 2f(x-h) - f(x-2h)] / (2h^3)
        交叉导: d2f/dxdy ≈ [f(x+h,y+k) - f(x+h,y-k) - f(x-h,y+k) + f(x-h,y-k)] / (4hk)
    """
    h_S = max(S * 0.001, 0.01)
    h_sigma = max(sigma * 0.01, 0.0001)
    h_r = 0.0001
    h_T = 1.0 / 365  # 1天

    base_price = pricing_func(S, K, T, r, sigma, option_type, **kwargs)

    if abs(base_price) < 1e-12:
        return _zero_greeks()

    # ============ 标准Greeks ============

    # Delta (dV/dS)
    price_S_up = pricing_func(S + h_S, K, T, r, sigma, option_type, **kwargs)
    price_S_dn = pricing_func(S - h_S, K, T, r, sigma, option_type, **kwargs)
    delta = (price_S_up - price_S_dn) / (2 * h_S)

    # Gamma (d2V/dS2)
    gamma = (price_S_up - 2 * base_price + price_S_dn) / (h_S ** 2)

    # Vega (dV/dsigma)
    price_v_up = pricing_func(S, K, T, r, sigma + h_sigma, option_type, **kwargs)
    price_v_dn = pricing_func(S, K, T, r, sigma - h_sigma, option_type, **kwargs)
    vega = (price_v_up - price_v_dn) / (2 * h_sigma)

    # Rho (dV/dr)
    price_r_up = pricing_func(S, K, T, r + h_r, sigma, option_type, **kwargs)
    price_r_dn = pricing_func(S, K, T, r - h_r, sigma, option_type, **kwargs)
    rho = (price_r_up - price_r_dn) / (2 * h_r)

    # Theta (dV/dt, 时间减少 -> 价格变化为负)
    price_t_dn = pricing_func(S, K, max(T - h_T, 0.001), r, sigma, option_type, **kwargs)
    theta = (price_t_dn - base_price) / h_T

    # ============ 二阶交叉 Greeks ============

    # Vanna = dDelta/dsigma = d2V/(dS*dsigma)
    # 交叉导数: [V(S+h, sig+h) - V(S+h, sig-h) - V(S-h, sig+h) + V(S-h, sig-h)] / (4*hS*hsig)
    price_SuVu = pricing_func(S + h_S, K, T, r, sigma + h_sigma, option_type, **kwargs)
    price_SuVd = pricing_func(S + h_S, K, T, r, sigma - h_sigma, option_type, **kwargs)
    price_SdVu = pricing_func(S - h_S, K, T, r, sigma + h_sigma, option_type, **kwargs)
    price_SdVd = pricing_func(S - h_S, K, T, r, sigma - h_sigma, option_type, **kwargs)
    vanna = (price_SuVu - price_SuVd - price_SdVu + price_SdVd) / (4 * h_S * h_sigma)

    # Volga/Vomma = d2V/dsigma2 = dVega/dsigma
    volga = (price_v_up - 2 * base_price + price_v_dn) / (h_sigma ** 2)

    # Charm = dDelta/dt = [Delta(T) - Delta(T-h)] / h_T
    # Delta at T-h
    price_t_Su = pricing_func(S + h_S, K, max(T - h_T, 0.001), r, sigma, option_type, **kwargs)
    price_t_Sd = pricing_func(S - h_S, K, max(T - h_T, 0.001), r, sigma, option_type, **kwargs)
    delta_t_dn = (price_t_Su - price_t_Sd) / (2 * h_S)
    charm = (delta - delta_t_dn) / h_T

    # Veta = dVega/dt = [Vega(T) - Vega(T-h)] / h_T
    vega_t_dn = (price_t_Su + price_t_Sd - 2 * price_t_dn) / (h_sigma ** 2)
    # Actually vega at T-h: [price_t_Su_v - price_t_Sd_v] won't work easily
    # Use: vega_t_dn approx = (price_t_up - price_t_dn) / (2 * h_sigma) where price_t_up is at T-h
    price_t_Vu = pricing_func(S, K, max(T - h_T, 0.001), r, sigma + h_sigma, option_type, **kwargs)
    price_t_Vd = pricing_func(S, K, max(T - h_T, 0.001), r, sigma - h_sigma, option_type, **kwargs)
    vega_t_dn = (price_t_Vu - price_t_Vd) / (2 * h_sigma)
    veta = (vega - vega_t_dn) / h_T

    # Color = dGamma/dt = [Gamma(T) - Gamma(T-h)] / h_T
    gamma_t_dn = (price_t_Su - 2 * price_t_dn + price_t_Sd) / (h_S ** 2)
    color = (gamma - gamma_t_dn) / h_T

    # Zomma = dGamma/dsigma = d2Gamma/(dS*dsigma) ≈ [Gamma(S+h, sig+h) - Gamma(S+h, sig-h) - Gamma(S-h, sig+h) + Gamma(S-h, sig-h)] / (4*hS*hsig)
    gamma_SuVu = (price_SuVu + pricing_func(S + 2*h_S, K, T, r, sigma + h_sigma, option_type, **kwargs) - 2*price_SuVu) / (h_S**2)
    # Simplified: Zomma ≈ dGamma/dsigma using central difference
    gamma_v_up = (pricing_func(S + h_S, K, T, r, sigma + h_sigma, option_type, **kwargs)
                  - 2 * price_v_up + pricing_func(S - h_S, K, T, r, sigma + h_sigma, option_type, **kwargs)) / (h_S ** 2)
    gamma_v_dn = (pricing_func(S + h_S, K, T, r, sigma - h_sigma, option_type, **kwargs)
                  - 2 * price_v_dn + pricing_func(S - h_S, K, T, r, sigma - h_sigma, option_type, **kwargs)) / (h_S ** 2)
    zomma = (gamma_v_up - gamma_v_dn) / (2 * h_sigma)

    # ============ 三阶 Greeks ============

    # Speed = d3V/dS3 = dGamma/dS
    # 三点公式: [f(x+2h) - 2f(x+h) + 2f(x-h) - f(x-2h)] / (2h^3)
    price_S_2up = pricing_func(S + 2 * h_S, K, T, r, sigma, option_type, **kwargs)
    price_S_2dn = pricing_func(S - 2 * h_S, K, T, r, sigma, option_type, **kwargs)
    speed = (price_S_2up - 2 * price_S_up + 2 * price_S_dn - price_S_2dn) / (2 * h_S ** 3)

    # Ultima = d3V/dsigma3 = dVolga/dsigma
    price_v_2up = pricing_func(S, K, T, r, sigma + 2 * h_sigma, option_type, **kwargs)
    price_v_2dn = pricing_func(S, K, T, r, sigma - 2 * h_sigma, option_type, **kwargs)
    ultima = (price_v_2up - 2 * price_v_up + 2 * price_v_dn - price_v_2dn) / (2 * h_sigma ** 3)

    # Lambda (elasticity)
    lam = delta * S / base_price if abs(base_price) > 1e-10 else 0.0

    return {
        # 一阶
        "delta": float(delta),
        "vega": float(vega / 100),
        "theta": float(theta / 365),
        "rho": float(rho / 100),
        # 二阶
        "gamma": float(gamma),
        "vanna": float(vanna / 100),
        "volga": float(volga / 100),
        "charm": float(charm / 365),
        "veta": float(veta / 365),
        "color": float(color / 365),
        "zomma": float(zomma / 100),
        # 三阶
        "speed": float(speed),
        "ultima": float(ultima / 10000),
        # 其他
        "lambda": float(lam),
    }


# ============ 向后兼容: 简版Greeks接口 ============

def _bsm_greeks(S: float, K: float, T: float, r: float, sigma: float,
                option_type: str = "call") -> dict:
    """欧式期权BSM Greeks(简版,向后兼容)"""
    full = _bsm_greeks_full(S, K, T, r, sigma, option_type)
    return {
        "delta": full["delta"],
        "gamma": full["gamma"],
        "vega": full["vega"],
        "theta": full["theta"],
        "rho": full["rho"],
    }


def _finite_difference_greeks(pricing_func, S: float, K: float, T: float, r: float, sigma: float,
                               option_type: str = "call", **kwargs) -> dict:
    """有限差分Greeks(简版,向后兼容)"""
    full = _finite_difference_greeks_full(pricing_func, S, K, T, r, sigma, option_type, **kwargs)
    return {
        "delta": full["delta"],
        "gamma": full["gamma"],
        "vega": full["vega"],
        "theta": full["theta"],
        "rho": full["rho"],
    }


# ============ 主入口 ============

def calculate_greeks(S: float, K: float, T: float, r: float, sigma: float,
                     option_type: str = "call", pricing_model: str = "european",
                     full: bool = True, **kwargs) -> dict:
    """
    计算期权Greeks

    参数:
        S, K, T, r, sigma: 标准BSM参数
        option_type: "call" 或 "put"
        pricing_model: 期权定价模型类型
        full: True返回完整14个Greeks, False返回简版5个标准Greeks

    返回:
        full=True: {delta, gamma, vega, theta, rho, vanna, volga, charm, veta, color, zomma, speed, ultima, lambda}
        full=False: {delta, gamma, vega, theta, rho}
    """
    if full:
        return _calculate_greeks_full(S, K, T, r, sigma, option_type, pricing_model, **kwargs)
    else:
        return _calculate_greeks_simple(S, K, T, r, sigma, option_type, pricing_model, **kwargs)


def _calculate_greeks_simple(S: float, K: float, T: float, r: float, sigma: float,
                              option_type: str, pricing_model: str, **kwargs) -> dict:
    """简版Greeks(5个标准)"""
    if pricing_model == "european":
        return _bsm_greeks(S, K, T, r, sigma, option_type)
    elif pricing_model == "american":
        from pricing.american import american_option
        return _finite_difference_greeks(american_option, S, K, T, r, sigma, option_type)
    elif pricing_model == "asian":
        from pricing.asian import asian_option
        obs_type = kwargs.get("observation_type", "arithmetic")
        return _finite_difference_greeks(
            asian_option, S, K, T, r, sigma, option_type, observation_type=obs_type)
    elif pricing_model == "barrier":
        from pricing.exotic import barrier_option
        H_val = kwargs.get("barrier_level", S * 1.1)
        bt_val = kwargs.get("barrier_type", "up_and_out")
        def _barrier_w(S, K, T, r, sigma, call_put="call", **kw):
            return barrier_option(S, K, T, r, sigma, H_val, bt_val, call_put)
        return _finite_difference_greeks(_barrier_w, S, K, T, r, sigma, option_type)
    elif pricing_model == "lookback":
        from pricing.exotic import lookback_option
        st = kwargs.get("strike_type", "fixed")
        return _finite_difference_greeks(
            lookback_option, S, K, T, r, sigma, option_type, strike_type=st)
    else:
        _pf = _get_pricing_func(pricing_model)
        if _pf:
            _extra = _get_extra_kwargs(pricing_model, kwargs)
            return _finite_difference_greeks(_pf, S, K, T, r, sigma, option_type, **_extra)
        return {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0, "rho": 0.0}


def _calculate_greeks_full(S: float, K: float, T: float, r: float, sigma: float,
                           option_type: str, pricing_model: str, **kwargs) -> dict:
    """完整版Greeks(14个)"""
    if pricing_model == "european":
        return _bsm_greeks_full(S, K, T, r, sigma, option_type)

    if pricing_model == "american":
        from pricing.american import american_option
        return _finite_difference_greeks_full(american_option, S, K, T, r, sigma, option_type)
    elif pricing_model == "asian":
        from pricing.asian import asian_option
        obs_type = kwargs.get("observation_type", "arithmetic")
        return _finite_difference_greeks_full(
            asian_option, S, K, T, r, sigma, option_type, observation_type=obs_type)
    elif pricing_model == "barrier":
        from pricing.exotic import barrier_option
        H_val = kwargs.get("barrier_level", S * 1.1)
        bt_val = kwargs.get("barrier_type", "up_and_out")
        def _barrier_w(S, K, T, r, sigma, call_put="call", **kw):
            return barrier_option(S, K, T, r, sigma, H_val, bt_val, call_put)
        return _finite_difference_greeks_full(_barrier_w, S, K, T, r, sigma, option_type)
    elif pricing_model == "lookback":
        from pricing.exotic import lookback_option
        st = kwargs.get("strike_type", "fixed")
        return _finite_difference_greeks_full(
            lookback_option, S, K, T, r, sigma, option_type, strike_type=st)
    else:
        _pf = _get_pricing_func(pricing_model)
        if _pf:
            _extra = _get_extra_kwargs(pricing_model, kwargs)
            return _finite_difference_greeks_full(_pf, S, K, T, r, sigma, option_type, **_extra)
        return _zero_greeks()


def _get_pricing_func(model: str):
    """获取新增奇异期权的定价函数(适配为标准签名 S,K,T,r,sigma,option_type,**kwargs)"""
    from pricing import exotic_advanced as ea

    def _wrap_binary(S, K, T, r, sigma, option_type="call", **kw):
        return ea.binary_option(S, K, T, r, sigma, option_type,
                               binary_type=kw.get("binary_type", "cash_or_nothing"),
                               payoff=kw.get("payoff", 1.0))

    def _wrap_chooser(S, K, T, r, sigma, option_type="call", **kw):
        return ea.chooser_option(S, K, T, r, sigma,
                                choose_time=kw.get("choose_time"),
                                K_put=kw.get("K_put"))

    def _wrap_compound(S, K, T, r, sigma, option_type="call", **kw):
        return ea.compound_option(S, kw.get("K1", K), kw.get("K2", K),
                                kw.get("T1", T*0.5), kw.get("T2", T),
                                r, sigma,
                                compound_type=kw.get("compound_type", "call_on_call"))

    def _wrap_forward_start(S, K, T, r, sigma, option_type="call", **kw):
        return ea.forward_start_option(S, K, T, r, sigma,
                                      start_time=kw.get("start_time"),
                                      alpha=kw.get("alpha", 1.0),
                                      option_type=option_type)

    def _wrap_power(S, K, T, r, sigma, option_type="call", **kw):
        return ea.power_option(S, K, T, r, sigma, option_type,
                              power=kw.get("power", 2.0))

    def _wrap_exchange(S, K, T, r, sigma, option_type="call", **kw):
        return ea.exchange_option(S, K, T, r, sigma,
                                 kw.get("sigma2", sigma*0.8),
                                 kw.get("rho", 0.5),
                                 option_type)

    def _wrap_cliquet(S, K, T, r, sigma, option_type="call", **kw):
        return ea.cliquet_option(S, K, T, r, sigma,
                                n_periods=kw.get("n_periods", 4),
                                cap=kw.get("cap", 0.10),
                                floor=kw.get("floor", 0.0),
                                option_type=option_type)

    def _wrap_shout(S, K, T, r, sigma, option_type="call", **kw):
        return ea.shout_option(S, K, T, r, sigma, option_type)

    def _wrap_double_barrier(S, K, T, r, sigma, option_type="call", **kw):
        return ea.double_barrier_option(S, K, T, r, sigma,
                                       H_lower=kw.get("H_lower", S*0.8),
                                       H_upper=kw.get("H_upper", S*1.2),
                                       option_type=option_type,
                                       barrier_type=kw.get("barrier_type", "knock_out"))

    def _wrap_range(S, K, T, r, sigma, option_type="call", **kw):
        return ea.range_option(S, T, r, sigma,
                             H_lower=kw.get("H_lower", S*0.8),
                             H_upper=kw.get("H_upper", S*1.2),
                             payoff=kw.get("payoff", 1.0),
                             range_type=kw.get("range_type", "inside"))

    def _wrap_quanto(S, K, T, r, sigma, option_type="call", **kw):
        return ea.quanto_option(S, K, T, r,
                               kw.get("r_f", 0.01),
                               sigma,
                               kw.get("sigma_fx", 0.10),
                               kw.get("rho", 0.0),
                               option_type)

    def _wrap_rainbow(S, K, T, r, sigma, option_type="call", **kw):
        return ea.rainbow_option(S, K, K, T, r, sigma,
                                kw.get("sigma2", sigma*0.8),
                                kw.get("rho", 0.5),
                                option_type=option_type,
                                rainbow_type=kw.get("rainbow_type", "best_of"))

    def _wrap_spread(S, K, T, r, sigma, option_type="call", **kw):
        return ea.spread_option(S, K, K, T, r, sigma,
                               kw.get("sigma2", sigma*0.8),
                               kw.get("rho", 0.5),
                               option_type=option_type)

    def _wrap_barrier_lookback(S, K, T, r, sigma, option_type="call", **kw):
        return ea.barrier_lookback_option(S, K, T, r, sigma,
                                        H=kw.get("barrier_level", S*1.1),
                                        barrier_type=kw.get("barrier_type", "up_and_out"),
                                        option_type=option_type,
                                        strike_type=kw.get("strike_type", "fixed"))

    func_map = {
        "binary": _wrap_binary,
        "digital": _wrap_binary,
        "chooser": _wrap_chooser,
        "compound": _wrap_compound,
        "forward_start": _wrap_forward_start,
        "power": _wrap_power,
        "exchange": _wrap_exchange,
        "cliquet": _wrap_cliquet,
        "shout": _wrap_shout,
        "double_barrier": _wrap_double_barrier,
        "range": _wrap_range,
        "quanto": _wrap_quanto,
        "rainbow": _wrap_rainbow,
        "spread": _wrap_spread,
        "barrier_lookback": _wrap_barrier_lookback,
    }
    return func_map.get(model)


def _get_extra_kwargs(model: str, kwargs: dict) -> dict:
    """根据期权类型获取额外参数(与包装器函数匹配,仅传递包装器需要的kwargs)"""
    extra = {}
    if model in ("binary", "digital"):
        extra["binary_type"] = kwargs.get("binary_type", "cash_or_nothing")
        extra["payoff"] = kwargs.get("payoff", 1.0)
    elif model == "chooser":
        extra["choose_time"] = kwargs.get("choose_time")
        extra["K_put"] = kwargs.get("K_put")
    elif model == "compound":
        extra["K1"] = kwargs.get("K1", 100.0)
        extra["K2"] = kwargs.get("K2", 100.0)
        extra["T1"] = kwargs.get("T1", 0.5)
        extra["T2"] = kwargs.get("T2", 1.0)
        extra["compound_type"] = kwargs.get("compound_type", "call_on_call")
    elif model == "forward_start":
        extra["start_time"] = kwargs.get("start_time")
        extra["alpha"] = kwargs.get("alpha", 1.0)
    elif model == "power":
        extra["power"] = kwargs.get("power", 2.0)
    elif model == "exchange":
        extra["sigma2"] = kwargs.get("sigma2", 0.2)
        extra["rho"] = kwargs.get("rho", 0.5)
    elif model == "cliquet":
        extra["n_periods"] = kwargs.get("n_periods", 4)
        extra["cap"] = kwargs.get("cap", 0.10)
        extra["floor"] = kwargs.get("floor", 0.0)
    elif model == "double_barrier":
        extra["H_lower"] = kwargs.get("H_lower", 100.0 * 0.8)
        extra["H_upper"] = kwargs.get("H_upper", 100.0 * 1.2)
        extra["barrier_type"] = kwargs.get("barrier_type", "knock_out")
    elif model == "range":
        extra["H_lower"] = kwargs.get("H_lower", 100.0 * 0.8)
        extra["H_upper"] = kwargs.get("H_upper", 100.0 * 1.2)
        extra["payoff"] = kwargs.get("payoff", 1.0)
        extra["range_type"] = kwargs.get("range_type", "inside")
    elif model == "quanto":
        extra["r_f"] = kwargs.get("r_f", 0.01)
        extra["sigma_fx"] = kwargs.get("sigma_fx", 0.10)
        extra["rho"] = kwargs.get("rho", 0.0)
    elif model == "rainbow":
        extra["sigma2"] = kwargs.get("sigma2", 0.2)
        extra["rho"] = kwargs.get("rho", 0.5)
        extra["rainbow_type"] = kwargs.get("rainbow_type", "best_of")
    elif model == "spread":
        extra["sigma2"] = kwargs.get("sigma2", 0.2)
        extra["rho"] = kwargs.get("rho", 0.5)
    elif model == "barrier_lookback":
        extra["barrier_level"] = kwargs.get("barrier_level", kwargs.get("H", 100.0 * 1.1))
        extra["barrier_type"] = kwargs.get("barrier_type", "up_and_out")
        extra["strike_type"] = kwargs.get("strike_type", "fixed")
    return extra
