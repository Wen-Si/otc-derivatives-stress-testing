"""
RSI(递归自我提升)路由

提供RSI自我进化引擎的API接口:
1. 触发RSI迭代训练
2. 查询RSI历史迭代记录
3. 查询最新RSI状态
4. 查询某轮迭代的评估明细
5. 查询当前应用的模型参数
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db, RSIEpoch, RSIEvaluationRecord
from services.rsi_engine import (
    run_rsi_iteration,
    get_rsi_history,
    get_rsi_latest,
    get_current_params,
    DEFAULT_MODEL_PARAMS,
    DEFAULT_CALIBRATION,
)

router = APIRouter()


@router.post("/rsi/run")
async def trigger_rsi(
    max_iterations: int = Query(3, ge=1, le=10, description="最大递归迭代次数"),
    db: Session = Depends(get_db),
):
    """
    触发RSI递归自我提升

    引擎将:
    1. 生成多场景测试样本(6种市场环境 x 全部持仓)
    2. 用高精度基准(500K蒙特卡洛/2000步二叉树/解析解)评估当前模型误差
    3. 基于误差自动优化参数(蒙特卡洛次数/二叉树步数/校准系数)
    4. 递归迭代直到收敛(提升幅度<2%)
    """
    try:
        result = await run_rsi_iteration(db, max_iterations=max_iterations)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RSI训练失败: {str(e)}")


@router.get("/rsi/history")
async def get_history(db: Session = Depends(get_db)):
    """获取RSI所有迭代轮次历史"""
    return {
        "success": True,
        "epochs": get_rsi_history(db),
    }


@router.get("/rsi/latest")
async def get_latest(db: Session = Depends(get_db)):
    """获取最新一轮RSI结果"""
    return get_rsi_latest(db)


@router.get("/rsi/params")
async def get_current_model_params(db: Session = Depends(get_db)):
    """获取当前应用的RSI优化参数(压力测试引擎实际使用的参数)"""
    params, calibration = get_current_params(db)
    latest = db.query(RSIEpoch).order_by(RSIEpoch.epoch.desc()).first()

    return {
        "model_params": params,
        "calibration_factors": calibration,
        "is_default": latest is None,
        "source_epoch": latest.epoch if latest else None,
        "default_model_params": DEFAULT_MODEL_PARAMS,
        "default_calibration": DEFAULT_CALIBRATION,
    }


@router.get("/rsi/records/{epoch_id}")
async def get_epoch_records(epoch_id: int, db: Session = Depends(get_db)):
    """获取某轮RSI迭代的评估明细(基准值 vs 预测值)"""
    epoch = db.query(RSIEpoch).filter(RSIEpoch.id == epoch_id).first()
    if not epoch:
        raise HTTPException(status_code=404, detail=f"RSI轮次不存在: {epoch_id}")

    records = db.query(RSIEvaluationRecord).filter(
        RSIEvaluationRecord.epoch_id == epoch_id
    ).all()

    return {
        "success": True,
        "epoch": {
            "id": epoch.id,
            "epoch": epoch.epoch,
            "name": epoch.name,
            "mae": epoch.mae,
            "rmse": epoch.rmse,
            "mape": epoch.mape,
            "r_squared": epoch.r_squared,
            "max_error": epoch.max_error,
            "converged": epoch.converged,
            "improvement_pct": epoch.improvement_pct,
            "n_samples": epoch.n_samples,
            "created_at": epoch.created_at.strftime("%Y-%m-%d %H:%M:%S") if epoch.created_at else "",
        },
        "records": [
            {
                "id": r.id,
                "position_id": r.position_id,
                "option_type": r.option_type,
                "call_put": r.call_put,
                "strike": r.strike,
                "benchmark_value": r.benchmark_value,
                "predicted_value": r.predicted_value,
                "abs_error": r.abs_error,
                "pct_error": r.pct_error,
                "S": r.S,
                "T": r.T,
                "r": r.r,
                "sigma": r.sigma,
            }
            for r in records
        ],
    }


@router.get("/rsi/status")
async def get_rsi_status(db: Session = Depends(get_db)):
    """获取RSI引擎整体状态概览"""
    total_epochs = db.query(RSIEpoch).count()
    latest = db.query(RSIEpoch).order_by(RSIEpoch.epoch.desc()).first()
    converged_count = db.query(RSIEpoch).filter(RSIEpoch.converged == True).count()

    params, calibration = get_current_params(db)

    return {
        "total_epochs": total_epochs,
        "converged_count": converged_count,
        "is_active": latest is not None,
        "latest_epoch": latest.epoch if latest else None,
        "latest_mae": latest.mae if latest else None,
        "latest_mape": latest.mape if latest else None,
        "latest_r_squared": latest.r_squared if latest else None,
        "latest_converged": latest.converged if latest else False,
        "latest_improvement_pct": latest.improvement_pct if latest else None,
        "current_model_params": params,
        "current_calibration": calibration,
        "is_using_default": latest is None,
    }
