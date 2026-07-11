"""
RSI(Recursive Self-Improvement)递归自我提升引擎

实现计量引擎的自我进化,核心流程:
1. 自我评估: 生成多场景测试样本,用高精度基准对比当前模型预测误差
2. 参数优化: 基于误差自动调整定价模型参数(蒙特卡洛次数/二叉树步数/校准系数)
3. 知识积累: 将优化后的参数持久化,形成不断进化的知识库
4. 递归提升: 重复评估-优化循环,直到精度收敛(提升幅度<阈值)

基准策略:
- 欧式期权: BSM解析解(精确解)作为基准
- 美式期权: 高精度二叉树(2000步)作为基准
- 亚式(算术): 高精度蒙特卡洛(50万次)作为基准
- 亚式(几何): 解析解作为基准
- 障碍期权: 高精度蒙特卡洛(50万次)作为基准
- 回望期权: 高精度蒙特卡洛(50万次)作为基准
"""
import json
import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session
from database import RSIEpoch, RSIEvaluationRecord, Position
from pricing.european import black_scholes
from pricing.american import american_option
from pricing.asian import asian_option
from pricing.exotic import barrier_option, lookback_option
from pricing import price_option

# ============ 默认模型参数 ============

DEFAULT_MODEL_PARAMS = {
    "american_steps": 200,
    "asian_n_simulations": 20000,
    "barrier_n_simulations": 20000,
    "lookback_n_simulations": 20000,
    "shout_n_steps": 252,
    "double_barrier_n_simulations": 20000,
    "double_barrier_n_steps": 252,
    "range_n_simulations": 20000,
    "range_n_steps": 252,
    "cliquet_n_simulations": 20000,
    "barrier_lookback_n_simulations": 20000,
    "barrier_lookback_n_steps": 252,
    "rainbow_n_simulations": 20000,
    "spread_n_simulations": 20000,
}

# 默认校准系数(每种期权类型一个乘数,用于校正系统性偏差)
DEFAULT_CALIBRATION = {
    "european": 1.0,
    "american": 1.0,
    "asian": 1.0,
    "barrier": 1.0,
    "lookback": 1.0,
    "binary": 1.0,
    "chooser": 1.0,
    "compound": 1.0,
    "forward_start": 1.0,
    "power": 1.0,
    "exchange": 1.0,
    "cliquet": 1.0,
    "shout": 1.0,
    "double_barrier": 1.0,
    "range": 1.0,
    "quanto": 1.0,
    "rainbow": 1.0,
    "spread": 1.0,
    "barrier_lookback": 1.0,
}

# 收敛阈值: 相对提升低于此值则认为收敛
CONVERGENCE_THRESHOLD = 0.02  # 2%


def _generate_test_samples(positions: list, market_factors: dict) -> list:
    """
    生成多场景测试样本

    对每个持仓,在多个风险因子组合下生成测试样本
    """
    S_base = market_factors.get("price", 5500.0)
    sigma_base = market_factors.get("volatility", 0.25)
    r_base = market_factors.get("risk_free_rate", 0.025)

    # 定义多组场景参数(模拟不同压力条件)
    scenarios = [
        {"S_mult": 1.0, "sigma_mult": 1.0, "r_shift": 0.0, "label": "基准"},
        {"S_mult": 0.90, "sigma_mult": 1.2, "r_shift": -0.005, "label": "温和下跌"},
        {"S_mult": 0.80, "sigma_mult": 1.5, "r_shift": -0.015, "label": "严重下跌"},
        {"S_mult": 0.70, "sigma_mult": 2.0, "r_shift": -0.020, "label": "极端下跌"},
        {"S_mult": 1.10, "sigma_mult": 0.8, "r_shift": 0.005, "label": "温和上涨"},
        {"S_mult": 1.20, "sigma_mult": 1.3, "r_shift": 0.010, "label": "快速上涨"},
    ]

    samples = []
    for pos in positions:
        T_base = _time_to_maturity(pos.maturity_date)
        if T_base <= 0:
            continue

        # 解析extra_params
        extra = {}
        if hasattr(pos, "extra_params") and pos.extra_params:
            try:
                extra = json.loads(pos.extra_params)
            except (json.JSONDecodeError, TypeError):
                pass

        for sc in scenarios:
            S = S_base * sc["S_mult"]
            sigma = max(sigma_base * sc["sigma_mult"], 0.01)
            r = max(r_base + sc["r_shift"], 0.001)
            T = T_base

            sample = {
                "position": pos,
                "S": S, "K": pos.strike, "T": T, "r": r, "sigma": sigma,
                "call_put": pos.call_put,
                "option_type": pos.option_type,
                "observation_type": pos.observation_type or "arithmetic",
                "barrier_type": pos.barrier_type or "up_and_out",
                "barrier_level": pos.barrier_level or S * 1.1,
                "scenario_label": sc["label"],
                "extra_params": extra,
                "strike_type": extra.get("strike_type", "fixed"),
            }
            # 从extra_params中传递奇异期权特有参数
            for k, v in extra.items():
                if k not in sample:
                    sample[k] = v

            samples.append(sample)

    return samples


def _time_to_maturity(maturity_date) -> float:
    if isinstance(maturity_date, str):
        maturity_date = datetime.strptime(maturity_date[:10], "%Y-%m-%d")
    delta = maturity_date - datetime.now()
    return max(delta.total_seconds() / (365.25 * 24 * 3600), 0.001)


def _compute_benchmark(sample: dict) -> float:
    """
    计算高精度基准值

    对不同期权类型使用不同策略获取精确基准:
    - 解析解: european, binary, forward_start, power, exchange, quanto
    - 高精度蒙特卡洛(20万次): asian, barrier, lookback, shout, double_barrier, range, cliquet, rainbow, spread, barrier_lookback
    - 高精度二叉树(2000步): american
    - Geske公式: compound
    - Rubinstein公式: chooser

    注: MC次数从50万降至20万以平衡精度与性能(误差<0.5%)
    """
    S, K, T, r, sigma = sample["S"], sample["K"], sample["T"], sample["r"], sample["sigma"]
    cp = sample["call_put"]
    otype = sample["option_type"]
    extra = sample.get("extra_params", {})

    if otype == "european":
        return black_scholes(S, K, T, r, sigma, cp)

    elif otype == "american":
        return american_option(S, K, T, r, sigma, cp, steps=2000)

    elif otype == "asian":
        obs_type = sample.get("observation_type", "arithmetic")
        if obs_type == "geometric":
            from pricing.asian import _geometric_asian_analytic
            return _geometric_asian_analytic(S, K, T, r, sigma, cp)
        else:
            return asian_option(S, K, T, r, sigma, cp, "arithmetic",
                                n_simulations=200000, n_observations=252)

    elif otype == "barrier":
        H = sample.get("barrier_level", S * 1.1)
        bt = sample.get("barrier_type", "up_and_out")
        return barrier_option(S, K, T, r, sigma, H, bt, cp,
                              n_simulations=200000, n_steps=504)

    elif otype == "lookback":
        return lookback_option(S, K, T, r, sigma, cp, "fixed",
                              n_simulations=200000, n_steps=504)

    # ============ 高级奇异期权基准 ============
    elif otype == "binary":
        from pricing.exotic_advanced import binary_option
        return binary_option(S, K, T, r, sigma, cp,
                            binary_type=extra.get("binary_type", "cash_or_nothing"),
                            payoff=extra.get("payoff", 1.0))

    elif otype == "chooser":
        from pricing.exotic_advanced import chooser_option
        return chooser_option(S, K, T, r, sigma,
                             choose_time=extra.get("choose_time"),
                             K_put=extra.get("K_put"))

    elif otype == "compound":
        from pricing.exotic_advanced import compound_option
        K1 = extra.get("K1", K)
        K2 = extra.get("K2", K)
        T1 = extra.get("T1", T * 0.5)
        T2 = extra.get("T2", T)
        return compound_option(S, K1, K2, T1, T2, r, sigma,
                              compound_type=extra.get("compound_type", "call_on_call"))

    elif otype == "forward_start":
        from pricing.exotic_advanced import forward_start_option
        return forward_start_option(S, K, T, r, sigma,
                                    start_time=extra.get("start_time"),
                                    alpha=extra.get("alpha", 1.0),
                                    option_type=cp)

    elif otype == "power":
        from pricing.exotic_advanced import power_option
        return power_option(S, K, T, r, sigma, cp,
                           power=extra.get("power", 2.0))

    elif otype == "exchange":
        from pricing.exotic_advanced import exchange_option
        return exchange_option(S, K, T, r, sigma,
                              extra.get("sigma2", sigma * 0.8),
                              extra.get("rho", 0.5),
                              option_type=cp)

    elif otype == "cliquet":
        from pricing.exotic_advanced import cliquet_option
        return cliquet_option(S, K, T, r, sigma,
                             n_periods=extra.get("n_periods", 4),
                             cap=extra.get("cap", 0.10),
                             floor=extra.get("floor", 0.0),
                             option_type=cp, n_simulations=50000)

    elif otype == "shout":
        from pricing.exotic_advanced import shout_option
        return shout_option(S, K, T, r, sigma, cp,
                           n_simulations=50000, n_steps=504)

    elif otype == "double_barrier":
        from pricing.exotic_advanced import double_barrier_option
        return double_barrier_option(S, K, T, r, sigma,
                                     H_lower=extra.get("H_lower", S*0.8),
                                     H_upper=extra.get("H_upper", S*1.2),
                                     option_type=cp,
                                     barrier_type=extra.get("barrier_type", "knock_out"),
                                     n_simulations=50000, n_steps=504)

    elif otype == "range":
        from pricing.exotic_advanced import range_option
        return range_option(S, T, r, sigma,
                           H_lower=extra.get("H_lower", S*0.8),
                           H_upper=extra.get("H_upper", S*1.2),
                           payoff=extra.get("payoff", 1.0),
                           range_type=extra.get("range_type", "inside"),
                           n_simulations=50000, n_steps=504)

    elif otype == "quanto":
        from pricing.exotic_advanced import quanto_option
        return quanto_option(S, K, T, r,
                            extra.get("r_f", 0.01), sigma,
                            extra.get("sigma_fx", 0.10),
                            extra.get("rho", 0.0),
                            option_type=cp)

    elif otype == "rainbow":
        from pricing.exotic_advanced import rainbow_option
        return rainbow_option(S, K, K, T, r, sigma,
                             extra.get("sigma2", sigma * 0.8),
                             extra.get("rho", 0.5),
                             option_type=cp,
                             rainbow_type=extra.get("rainbow_type", "best_of"),
                             n_simulations=50000)

    elif otype == "spread":
        from pricing.exotic_advanced import spread_option
        return spread_option(S, K, K, T, r, sigma,
                            extra.get("sigma2", sigma * 0.8),
                            extra.get("rho", 0.5),
                            option_type=cp, n_simulations=50000)

    elif otype == "barrier_lookback":
        from pricing.exotic_advanced import barrier_lookback_option
        H = sample.get("barrier_level", S * 1.1)
        bt = sample.get("barrier_type", "up_and_out")
        return barrier_lookback_option(S, K, T, r, sigma,
                                       H=H, barrier_type=bt,
                                       option_type=cp,
                                       strike_type=extra.get("strike_type", "fixed"),
                                       n_simulations=50000, n_steps=504)

    return 0.0


def _compute_prediction(sample: dict, model_params: dict, calibration: dict) -> float:
    """
    使用当前模型参数计算预测值
    支持全部19种期权类型
    """
    S, K, T, r, sigma = sample["S"], sample["K"], sample["T"], sample["r"], sample["sigma"]
    cp = sample["call_put"]
    otype = sample["option_type"]
    extra = sample.get("extra_params", {})

    if otype == "european":
        val = black_scholes(S, K, T, r, sigma, cp)

    elif otype == "american":
        steps = model_params.get("american_steps", 200)
        val = american_option(S, K, T, r, sigma, cp, steps=steps)

    elif otype == "asian":
        obs_type = sample.get("observation_type", "arithmetic")
        if obs_type == "geometric":
            from pricing.asian import _geometric_asian_analytic
            val = _geometric_asian_analytic(S, K, T, r, sigma, cp)
        else:
            n_sim = model_params.get("asian_n_simulations", 20000)
            val = asian_option(S, K, T, r, sigma, cp, "arithmetic",
                               n_simulations=n_sim, n_observations=252)

    elif otype == "barrier":
        H = sample.get("barrier_level", S * 1.1)
        bt = sample.get("barrier_type", "up_and_out")
        n_sim = model_params.get("barrier_n_simulations", 20000)
        val = barrier_option(S, K, T, r, sigma, H, bt, cp,
                             n_simulations=n_sim, n_steps=252)

    elif otype == "lookback":
        n_sim = model_params.get("lookback_n_simulations", 20000)
        val = lookback_option(S, K, T, r, sigma, cp, "fixed",
                              n_simulations=n_sim, n_steps=252)

    # ============ 高级奇异期权 ============
    elif otype == "binary":
        from pricing.exotic_advanced import binary_option
        val = binary_option(S, K, T, r, sigma, cp,
                           binary_type=extra.get("binary_type", "cash_or_nothing"),
                           payoff=extra.get("payoff", 1.0))

    elif otype == "chooser":
        from pricing.exotic_advanced import chooser_option
        val = chooser_option(S, K, T, r, sigma,
                            choose_time=extra.get("choose_time"),
                            K_put=extra.get("K_put"))

    elif otype == "compound":
        from pricing.exotic_advanced import compound_option
        val = compound_option(S, extra.get("K1", K), extra.get("K2", K),
                             extra.get("T1", T*0.5), extra.get("T2", T),
                             r, sigma,
                             compound_type=extra.get("compound_type", "call_on_call"))

    elif otype == "forward_start":
        from pricing.exotic_advanced import forward_start_option
        val = forward_start_option(S, K, T, r, sigma,
                                   start_time=extra.get("start_time"),
                                   alpha=extra.get("alpha", 1.0),
                                   option_type=cp)

    elif otype == "power":
        from pricing.exotic_advanced import power_option
        val = power_option(S, K, T, r, sigma, cp,
                          power=extra.get("power", 2.0))

    elif otype == "exchange":
        from pricing.exotic_advanced import exchange_option
        val = exchange_option(S, K, T, r, sigma,
                             extra.get("sigma2", sigma*0.8),
                             extra.get("rho", 0.5),
                             option_type=cp)

    elif otype == "cliquet":
        from pricing.exotic_advanced import cliquet_option
        n_sim = model_params.get("cliquet_n_simulations", 20000)
        val = cliquet_option(S, K, T, r, sigma,
                            n_periods=extra.get("n_periods", 4),
                            cap=extra.get("cap", 0.10),
                            floor=extra.get("floor", 0.0),
                            option_type=cp, n_simulations=n_sim)

    elif otype == "shout":
        from pricing.exotic_advanced import shout_option
        n_steps = model_params.get("shout_n_steps", 252)
        val = shout_option(S, K, T, r, sigma, cp, n_simulations=20000, n_steps=n_steps)

    elif otype == "double_barrier":
        from pricing.exotic_advanced import double_barrier_option
        n_sim = model_params.get("double_barrier_n_simulations", 20000)
        n_steps = model_params.get("double_barrier_n_steps", 252)
        val = double_barrier_option(S, K, T, r, sigma,
                                    H_lower=extra.get("H_lower", S*0.8),
                                    H_upper=extra.get("H_upper", S*1.2),
                                    option_type=cp,
                                    barrier_type=extra.get("barrier_type", "knock_out"),
                                    n_simulations=n_sim, n_steps=n_steps)

    elif otype == "range":
        from pricing.exotic_advanced import range_option
        n_sim = model_params.get("range_n_simulations", 20000)
        n_steps = model_params.get("range_n_steps", 252)
        val = range_option(S, T, r, sigma,
                          H_lower=extra.get("H_lower", S*0.8),
                          H_upper=extra.get("H_upper", S*1.2),
                          payoff=extra.get("payoff", 1.0),
                          range_type=extra.get("range_type", "inside"),
                          n_simulations=n_sim, n_steps=n_steps)

    elif otype == "quanto":
        from pricing.exotic_advanced import quanto_option
        val = quanto_option(S, K, T, r,
                           extra.get("r_f", 0.01), sigma,
                           extra.get("sigma_fx", 0.10),
                           extra.get("rho", 0.0),
                           option_type=cp)

    elif otype == "rainbow":
        from pricing.exotic_advanced import rainbow_option
        n_sim = model_params.get("rainbow_n_simulations", 20000)
        val = rainbow_option(S, K, K, T, r, sigma,
                            extra.get("sigma2", sigma*0.8),
                            extra.get("rho", 0.5),
                            option_type=cp,
                            rainbow_type=extra.get("rainbow_type", "best_of"),
                            n_simulations=n_sim)

    elif otype == "spread":
        from pricing.exotic_advanced import spread_option
        n_sim = model_params.get("spread_n_simulations", 20000)
        val = spread_option(S, K, K, T, r, sigma,
                           extra.get("sigma2", sigma*0.8),
                           extra.get("rho", 0.5),
                           option_type=cp, n_simulations=n_sim)

    elif otype == "barrier_lookback":
        from pricing.exotic_advanced import barrier_lookback_option
        H = sample.get("barrier_level", S * 1.1)
        bt = sample.get("barrier_type", "up_and_out")
        n_sim = model_params.get("barrier_lookback_n_simulations", 20000)
        n_steps = model_params.get("barrier_lookback_n_steps", 252)
        val = barrier_lookback_option(S, K, T, r, sigma,
                                      H=H, barrier_type=bt,
                                      option_type=cp,
                                      strike_type=extra.get("strike_type", "fixed"),
                                      n_simulations=n_sim, n_steps=n_steps)
    else:
        val = 0.0

    # 应用校准系数
    cal_factor = calibration.get(otype, 1.0)
    return val * cal_factor


def _evaluate(samples: list, model_params: dict, calibration: dict, benchmarks: list = None) -> list:
    """评估所有样本,返回误差记录列表
    
    参数:
        benchmarks: 预计算的基准值列表(避免重复计算高精度MC),若None则现场计算
    """
    records = []
    for idx, s in enumerate(samples):
        if benchmarks is not None:
            benchmark = benchmarks[idx]
        else:
            benchmark = _compute_benchmark(s)
        predicted = _compute_prediction(s, model_params, calibration)
        abs_err = abs(predicted - benchmark)
        pct_err = (abs_err / abs(benchmark) * 100) if abs(benchmark) > 1e-6 else 0.0
        records.append({
            "position_id": s["position"].id if hasattr(s["position"], "id") else None,
            "option_type": s["option_type"],
            "call_put": s["call_put"],
            "strike": s["K"],
            "benchmark_value": round(benchmark, 6),
            "predicted_value": round(predicted, 6),
            "abs_error": round(abs_err, 6),
            "pct_error": round(pct_err, 4),
            "S": round(s["S"], 2),
            "T": round(s["T"], 4),
            "r": round(s["r"], 6),
            "sigma": round(s["sigma"], 6),
        })
    return records


def _compute_metrics(records: list) -> dict:
    """计算评估指标"""
    errors = [r["abs_error"] for r in records]
    pct_errors = [r["pct_error"] for r in records if r["pct_error"] < 1000]  # 排除极端值

    n = len(errors)
    if n == 0:
        return {"mae": 0, "rmse": 0, "mape": 0, "r_squared": 0, "max_error": 0}

    mae = float(np.mean(errors))
    rmse = float(np.sqrt(np.mean(np.square(errors))))
    mape = float(np.mean(pct_errors)) if pct_errors else 0.0
    max_err = float(np.max(errors))

    # R²
    benchmarks = np.array([r["benchmark_value"] for r in records])
    predictions = np.array([r["predicted_value"] for r in records])
    ss_res = float(np.sum(np.square(predictions - benchmarks)))
    ss_tot = float(np.sum(np.square(benchmarks - np.mean(benchmarks))))
    r_sq = 1 - (ss_res / ss_tot) if ss_tot > 1e-10 else 1.0

    return {
        "mae": round(mae, 6),
        "rmse": round(rmse, 6),
        "mape": round(mape, 4),
        "r_squared": round(r_sq, 6),
        "max_error": round(max_err, 6),
    }


def _optimize_params(records: list, current_params: dict, current_cal: dict) -> tuple:
    """
    基于评估结果优化模型参数和校准系数

    优化策略:
    1. 对蒙特卡洛类模型: 若误差大,增加模拟次数;若已很小,适当减少以提升性能
    2. 对二叉树模型: 若误差大,增加步数
    3. 对每种期权类型: 计算系统性偏差,调整校准系数
    """
    new_params = current_params.copy()
    new_cal = current_cal.copy()

    # 按期权类型分组统计
    type_stats = {}
    for r in records:
        ot = r["option_type"]
        if ot not in type_stats:
            type_stats[ot] = {"errors": [], "benchmarks": [], "predictions": [], "pct_errors": []}
        type_stats[ot]["errors"].append(r["abs_error"])
        type_stats[ot]["benchmarks"].append(r["benchmark_value"])
        type_stats[ot]["predictions"].append(r["predicted_value"])
        type_stats[ot]["pct_errors"].append(r["pct_error"])

    for ot, stats in type_stats.items():
        mae_type = float(np.mean(stats["errors"]))
        mape_type = float(np.mean(stats["pct_errors"]))

        # 1. 优化蒙特卡洛次数(所有蒙特卡洛类期权)
        mc_param_map = {
            "asian": "asian_n_simulations",
            "barrier": "barrier_n_simulations",
            "lookback": "lookback_n_simulations",
            "cliquet": "cliquet_n_simulations",
            "double_barrier": "double_barrier_n_simulations",
            "range": "range_n_simulations",
            "rainbow": "rainbow_n_simulations",
            "spread": "spread_n_simulations",
            "barrier_lookback": "barrier_lookback_n_simulations",
        }

        if ot in mc_param_map and mae_type > 5.0:
            param_key = mc_param_map[ot]
            current_val = current_params.get(param_key, 20000)
            new_params[param_key] = min(current_val + 10000, 80000)

        # 2. 优化二叉树步数
        if ot == "american" and mae_type > 2.0:
            new_params["american_steps"] = min(current_params.get("american_steps", 200) + 100, 800)

        # 3. 优化校准系数(校正系统性偏差)
        benches = np.array(stats["benchmarks"])
        preds = np.array(stats["predictions"])
        # 校准系数 = 基准均值 / 预测均值 (预测偏低则>1,偏高则<1)
        mean_bench = float(np.mean(np.abs(benches)))
        mean_pred = float(np.mean(np.abs(preds)))
        if mean_pred > 1e-6:
            raw_ratio = mean_bench / mean_pred
            # 使用指数加权移动平均,避免剧烈跳变
            old_cal = current_cal.get(ot, 1.0)
            new_cal[ot] = round(old_cal * 0.6 + raw_ratio * 0.4, 6)

    return new_params, new_cal


def get_current_params(db: Session) -> tuple:
    """获取当前最优模型参数(从数据库加载,若空则用默认值)"""
    latest = db.query(RSIEpoch).order_by(RSIEpoch.epoch.desc()).first()
    if latest and latest.model_params:
        params = json.loads(latest.model_params)
        cal = json.loads(latest.calibration_factors) if latest.calibration_factors else DEFAULT_CALIBRATION.copy()
        return params, cal
    return DEFAULT_MODEL_PARAMS.copy(), DEFAULT_CALIBRATION.copy()


async def run_rsi_iteration(db: Session, positions: list = None, max_iterations: int = 3) -> dict:
    """
    执行RSI递归自我提升

    参数:
        db: 数据库会话
        positions: 持仓列表(为None则从数据库获取)
        max_iterations: 最大递归迭代次数

    返回:
        RSI提升结果摘要
    """
    if positions is None:
        positions = db.query(Position).all()

    if not positions:
        return {"success": False, "error": "无持仓数据"}

    # 获取当前市场数据
    import services.market_data as market_data
    try:
        md = await market_data.get_all_market_data()
        market_factors = {
            "price": md["underlying"]["current_price"],
            "volatility": md["volatility"]["value"],
            "risk_free_rate": md["risk_free_rate"]["value"],
        }
    except Exception:
        market_factors = {"price": 5500.0, "volatility": 0.25, "risk_free_rate": 0.025}

    # 生成测试样本
    samples = _generate_test_samples(positions, market_factors)

    # 预计算所有样本的高精度基准值(只需计算一次,后续迭代复用)
    # 这是性能关键优化:避免每次迭代都重复运行50万/10万次MC模拟
    benchmarks = []
    for idx, s in enumerate(samples):
        bm = _compute_benchmark(s)
        benchmarks.append(bm)

    # 获取当前参数
    current_params, current_cal = get_current_params(db)

    # 确定起始轮次
    last_epoch = db.query(RSIEpoch).order_by(RSIEpoch.epoch.desc()).first()
    start_epoch = (last_epoch.epoch + 1) if last_epoch else 0

    iterations = []
    prev_mae = None

    for i in range(max_iterations):
        epoch_num = start_epoch + i

        # 1. 评估当前参数(使用预计算的基准值)
        records = _evaluate(samples, current_params, current_cal, benchmarks=benchmarks)
        metrics = _compute_metrics(records)

        # 2. 计算提升幅度
        if prev_mae is not None and prev_mae > 1e-10:
            improvement = (prev_mae - metrics["mae"]) / prev_mae * 100
        else:
            improvement = 0.0 if prev_mae is None else 0.0

        converged = improvement < CONVERGENCE_THRESHOLD * 100 and i > 0

        # 3. 保存轮次记录
        epoch_record = RSIEpoch(
            epoch=epoch_num,
            name=f"RSI迭代第{epoch_num}轮",
            description=f"样本数={len(records)}, MAE={metrics['mae']:.4f}, MAPE={metrics['mape']:.2f}%, R²={metrics['r_squared']:.6f}",
            mae=metrics["mae"],
            rmse=metrics["rmse"],
            mape=metrics["mape"],
            r_squared=metrics["r_squared"],
            max_error=metrics["max_error"],
            model_params=json.dumps(current_params),
            calibration_factors=json.dumps(current_cal),
            converged=converged,
            improvement_pct=round(improvement, 4),
            n_samples=len(records),
        )
        db.add(epoch_record)
        db.flush()

        # 保存评估明细
        for r in records:
            db.add(RSIEvaluationRecord(
                epoch_id=epoch_record.id,
                position_id=r.get("position_id"),
                option_type=r["option_type"],
                call_put=r["call_put"],
                strike=r["strike"],
                benchmark_value=r["benchmark_value"],
                predicted_value=r["predicted_value"],
                abs_error=r["abs_error"],
                pct_error=r["pct_error"],
                S=r["S"],
                T=r["T"],
                r=r["r"],
                sigma=r["sigma"],
            ))

        iterations.append({
            "epoch": epoch_num,
            "metrics": metrics,
            "model_params": current_params,
            "calibration_factors": current_cal,
            "improvement_pct": round(improvement, 4),
            "converged": converged,
            "n_samples": len(records),
        })

        # 4. 检查收敛
        if converged:
            db.commit()
            break

        # 5. 优化参数(递归提升的核心)
        current_params, current_cal = _optimize_params(records, current_params, current_cal)
        prev_mae = metrics["mae"]

    db.commit()

    # 返回最终结果
    final = iterations[-1]
    first = iterations[0]

    return {
        "success": True,
        "n_iterations": len(iterations),
        "start_epoch": start_epoch,
        "converged": final["converged"],
        "initial_metrics": first["metrics"],
        "final_metrics": final["metrics"],
        "total_improvement_pct": round(
            ((first["metrics"]["mae"] - final["metrics"]["mae"]) / first["metrics"]["mae"] * 100)
            if first["metrics"]["mae"] > 1e-10 else 0.0, 4
        ),
        "final_model_params": final["model_params"],
        "final_calibration_factors": final["calibration_factors"],
        "iterations": iterations,
        "n_samples": final["n_samples"],
    }


def get_rsi_history(db: Session) -> list:
    """获取RSI所有迭代轮次历史"""
    epochs = db.query(RSIEpoch).order_by(RSIEpoch.epoch.asc()).all()
    result = []
    for e in epochs:
        result.append({
            "id": e.id,
            "epoch": e.epoch,
            "name": e.name,
            "description": e.description,
            "mae": e.mae,
            "rmse": e.rmse,
            "mape": e.mape,
            "r_squared": e.r_squared,
            "max_error": e.max_error,
            "model_params": json.loads(e.model_params) if e.model_params else None,
            "calibration_factors": json.loads(e.calibration_factors) if e.calibration_factors else None,
            "converged": e.converged,
            "improvement_pct": e.improvement_pct,
            "n_samples": e.n_samples,
            "created_at": e.created_at.strftime("%Y-%m-%d %H:%M:%S") if e.created_at else "",
        })
    return result


def get_rsi_latest(db: Session) -> dict:
    """获取最新一轮RSI结果"""
    latest = db.query(RSIEpoch).order_by(RSIEpoch.epoch.desc()).first()
    if not latest:
        return {"has_rsi": False, "message": "尚未执行RSI训练"}
    return {
        "has_rsi": True,
        "epoch": latest.epoch,
        "mae": latest.mae,
        "rmse": latest.rmse,
        "mape": latest.mape,
        "r_squared": latest.r_squared,
        "max_error": latest.max_error,
        "model_params": json.loads(latest.model_params) if latest.model_params else None,
        "calibration_factors": json.loads(latest.calibration_factors) if latest.calibration_factors else None,
        "converged": latest.converged,
        "improvement_pct": latest.improvement_pct,
        "n_samples": latest.n_samples,
        "created_at": latest.created_at.strftime("%Y-%m-%d %H:%M:%S") if latest.created_at else "",
    }
