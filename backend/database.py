"""
场外衍生品智能压力测试平台 - 数据库模型与会话管理
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from config import settings

engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============ 数据库模型 ============

class Position(Base):
    """期权持仓表"""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="持仓名称")
    option_type = Column(String(50), nullable=False, comment="期权类型: european/american/asian/barrier/lookback")
    call_put = Column(String(10), nullable=False, comment="认购/认沽: call/put")
    underlying = Column(String(20), nullable=False, default="000905.SH", comment="标的资产代码")
    underlying_name = Column(String(50), nullable=False, default="中证500指数", comment="标的资产名称")
    strike = Column(Float, nullable=False, comment="行权价")
    maturity_date = Column(DateTime, nullable=False, comment="到期日")
    quantity = Column(Float, nullable=False, default=1.0, comment="合约数量")
    position_direction = Column(String(10), nullable=False, default="long", comment="多头/空头: long/short")
    notional = Column(Float, nullable=False, comment="名义本金")
    barrier_type = Column(String(50), nullable=True, comment="障碍类型: up_and_out/down_and_out/up_and_in/down_and_in/knock_out/knock_in")
    barrier_level = Column(Float, nullable=True, comment="障碍水平/障碍价格")
    observation_type = Column(String(50), nullable=True, comment="亚式观察类型: arithmetic/geometric; 也用于: strike_type=fixed/floating")
    entry_price = Column(Float, nullable=True, comment="入场价格")
    extra_params = Column(Text, nullable=True, comment="额外参数JSON(奇异期权): binary_type/payoff/power/choose_time/K1/K2/T1/T2/compound_type/alpha/n_periods/cap/floor/H_lower/H_upper/S1/S2/sigma1/sigma2/rho/rainbow_type/range_type/r_d/r_f/sigma_s/sigma_fx")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    stress_results = relationship("StressResult", back_populates="position")


class RiskFactor(Base):
    """风险因子表"""
    __tablename__ = "risk_factors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_name = Column(String(100), nullable=False, comment="风险因子名称")
    factor_type = Column(String(50), nullable=False, comment="因子类型: price/volatility/risk_free_rate")
    factor_code = Column(String(50), nullable=True, comment="因子代码(如000905.SH)")
    current_value = Column(Float, nullable=False, comment="当前值")
    unit = Column(String(20), nullable=True, comment="单位")
    source = Column(String(50), default="tushare", comment="数据来源")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class StressScenario(Base):
    """压力测试场景表"""
    __tablename__ = "stress_scenarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="场景名称")
    description = Column(Text, nullable=True, comment="场景描述")
    user_query = Column(Text, nullable=True, comment="用户原始查询")
    ai_generated = Column(Boolean, default=True, comment="是否AI生成")
    status = Column(String(20), default="completed", comment="状态: pending/running/completed/failed")
    total_pnl = Column(Float, nullable=True, comment="总盈亏变化")
    created_at = Column(DateTime, default=datetime.now)

    shocks = relationship("StressShock", back_populates="scenario", cascade="all, delete-orphan")
    results = relationship("StressResult", back_populates="scenario", cascade="all, delete-orphan")


class StressShock(Base):
    """压力冲击因子表"""
    __tablename__ = "stress_shocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(Integer, ForeignKey("stress_scenarios.id", ondelete="CASCADE"), nullable=False)
    factor_name = Column(String(100), nullable=False, comment="风险因子名称")
    factor_type = Column(String(50), nullable=False, comment="因子类型: price/volatility/risk_free_rate")
    shock_type = Column(String(20), nullable=False, comment="冲击类型: absolute/relative")
    shock_value = Column(Float, nullable=False, comment="冲击值")
    original_value = Column(Float, nullable=True, comment="原始值")
    shocked_value = Column(Float, nullable=True, comment="冲击后值")
    description = Column(String(500), nullable=True, comment="冲击描述")

    scenario = relationship("StressScenario", back_populates="shocks")


class StressResult(Base):
    """压力测试结果表"""
    __tablename__ = "stress_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(Integer, ForeignKey("stress_scenarios.id", ondelete="CASCADE"), nullable=False)
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="CASCADE"), nullable=False)
    original_value = Column(Float, nullable=False, comment="原始估值")
    stressed_value = Column(Float, nullable=False, comment="压力下估值")
    pnl_change = Column(Float, nullable=False, comment="盈亏变化")
    pnl_pct = Column(Float, nullable=True, comment="盈亏变化百分比")

    scenario = relationship("StressScenario", back_populates="results")
    position = relationship("Position", back_populates="stress_results")


# ============ RSI(递归自我提升)相关表 ============

class RSIEpoch(Base):
    """RSI训练轮次表 - 记录每一次自我提升迭代"""
    __tablename__ = "rsi_epochs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    epoch = Column(Integer, nullable=False, comment="迭代轮次(0=初始基线)")
    name = Column(String(200), nullable=False, comment="轮次名称")
    description = Column(Text, nullable=True, comment="本轮改进描述")
    # 评估指标
    mae = Column(Float, nullable=True, comment="平均绝对误差")
    rmse = Column(Float, nullable=True, comment="均方根误差")
    mape = Column(Float, nullable=True, comment="平均绝对百分比误差(%)")
    r_squared = Column(Float, nullable=True, comment="R²拟合优度")
    max_error = Column(Float, nullable=True, comment="最大单点误差")
    # 优化后的模型参数(JSON字符串)
    model_params = Column(Text, nullable=True, comment="优化后的定价模型参数JSON")
    # 校准系数(JSON字符串)
    calibration_factors = Column(Text, nullable=True, comment="各期权类型校准系数JSON")
    # 收敛状态
    converged = Column(Boolean, default=False, comment="是否已收敛")
    improvement_pct = Column(Float, nullable=True, comment="相对上一轮的提升百分比")
    n_samples = Column(Integer, nullable=True, comment="评估样本数")
    created_at = Column(DateTime, default=datetime.now)


class RSIEvaluationRecord(Base):
    """RSI单点评估记录 - 记录每个持仓在每次评估中的预测值与基准值"""
    __tablename__ = "rsi_evaluation_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    epoch_id = Column(Integer, ForeignKey("rsi_epochs.id", ondelete="CASCADE"), nullable=False)
    position_id = Column(Integer, nullable=True, comment="持仓ID")
    option_type = Column(String(50), nullable=False, comment="期权类型")
    call_put = Column(String(10), nullable=False, comment="认购/认沽")
    strike = Column(Float, nullable=False, comment="行权价")
    # 基准值(来自解析解或高精度蒙特卡洛)
    benchmark_value = Column(Float, nullable=False, comment="基准估值")
    # 当前模型预测值
    predicted_value = Column(Float, nullable=False, comment="模型预测估值")
    # 误差
    abs_error = Column(Float, nullable=False, comment="绝对误差")
    pct_error = Column(Float, nullable=True, comment="百分比误差(%)")
    # 场景参数
    S = Column(Float, nullable=True, comment="标的价格")
    T = Column(Float, nullable=True, comment="到期时间")
    r = Column(Float, nullable=True, comment="无风险利率")
    sigma = Column(Float, nullable=True, comment="波动率")
    created_at = Column(DateTime, default=datetime.now)


# ============ 数据库会话 ============

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """创建所有表"""
    Base.metadata.create_all(bind=engine)
