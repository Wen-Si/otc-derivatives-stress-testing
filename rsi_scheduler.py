"""
RSI定时自动运行脚本

此脚本在每日午夜自动触发RSI递归自我提升流程:
1. 检查后端服务是否运行
2. 调用RSI API执行自我进化
3. 输出结果摘要
4. 将结果记录到日志文件

使用方式:
    直接运行: python rsi_scheduler.py
    或通过Windows任务计划程序在每日0:00自动运行
"""
import sys
import os
import requests
import json
from datetime import datetime

# 添加backend路径
BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, BACKEND_DIR)

API_BASE = "http://localhost:8000/api"
LOG_FILE = os.path.join(BACKEND_DIR, "rsi_scheduler.log")


def log(message: str):
    """输出并记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def check_backend() -> bool:
    """检查后端服务是否运行"""
    try:
        r = requests.get(f"{API_BASE}/../api/health", timeout=10)
        return r.status_code == 200
    except Exception:
        return False


def run_rsi() -> dict:
    """触发RSI递归自我提升"""
    log("开始执行RSI递归自我提升...")

    # 获取RSI训练前状态
    try:
        r = requests.get(f"{API_BASE}/rsi/status", timeout=30)
        before = r.json()
        log(f"训练前状态: 总轮次={before.get('total_epochs', 0)}, "
            f"MAE={before.get('latest_mae', 'N/A')}, "
            f"使用默认参数={before.get('is_using_default', True)}")
    except Exception as e:
        log(f"获取训练前状态失败: {e}")
        before = {}

    # 执行RSI训练 (最大5轮迭代)
    try:
        r = requests.post(
            f"{API_BASE}/rsi/run?max_iterations=5",
            json={},
            timeout=900  # 15分钟超时(支持19种期权类型的高精度基准计算)
        )
        if r.status_code == 200:
            result = r.json()
            log(f"RSI训练完成!")
            log(f"  迭代轮数: {result.get('n_iterations', 0)}")
            log(f"  是否收敛: {result.get('converged', False)}")
            log(f"  初始MAE: {result.get('initial_metrics', {}).get('mae', 'N/A')}")
            log(f"  最终MAE: {result.get('final_metrics', {}).get('mae', 'N/A')}")
            log(f"  总提升: {result.get('total_improvement_pct', 0):.2f}%")
            log(f"  样本数: {result.get('n_samples', 0)}")
            log(f"  最终模型参数: {json.dumps(result.get('final_model_params', {}), ensure_ascii=False)}")
            log(f"  最终校准系数: {json.dumps(result.get('final_calibration_factors', {}), ensure_ascii=False)}")

            # 输出每轮迭代详情
            for it in result.get("iterations", []):
                m = it.get("metrics", {})
                log(f"    Epoch {it.get('epoch')}: MAE={m.get('mae', 0):.4f}, "
                    f"RMSE={m.get('rmse', 0):.4f}, "
                    f"R²={m.get('r_squared', 0):.6f}, "
                    f"提升={it.get('improvement_pct', 0):.2f}%, "
                    f"收敛={it.get('converged', False)}")

            return result
        else:
            log(f"RSI训练API返回错误: {r.status_code} - {r.text[:200]}")
            return {"success": False, "error": f"API {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        log(f"RSI训练异常: {e}")
        return {"success": False, "error": str(e)}


def verify_rsi():
    """验证RSI结果已应用"""
    try:
        r = requests.get(f"{API_BASE}/rsi/status", timeout=30)
        after = r.json()
        log(f"训练后状态: 总轮次={after.get('total_epochs', 0)}, "
            f"MAE={after.get('latest_mae', 'N/A')}, "
            f"收敛={after.get('latest_converged', False)}, "
            f"使用默认参数={after.get('is_using_default', True)}")
        return after
    except Exception as e:
        log(f"获取训练后状态失败: {e}")
        return {}


if __name__ == "__main__":
    log("=" * 60)
    log("RSI每日自动优化 - 开始执行")
    log("=" * 60)

    # 1. 检查后端服务
    if not check_backend():
        log("后端服务未运行，尝试启动...")
        # 尝试启动后端
        import subprocess
        try:
            subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
                cwd=BACKEND_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            log("等待后端启动...")
            import time
            time.sleep(10)
            if not check_backend():
                log("后端启动失败，退出")
                sys.exit(1)
            log("后端已启动")
        except Exception as e:
            log(f"启动后端失败: {e}")
            sys.exit(1)

    # 2. 执行RSI训练
    result = run_rsi()

    # 3. 验证结果
    verify_rsi()

    log("=" * 60)
    log("RSI每日自动优化 - 完成")
    log("=" * 60 + "\n")
