"""
数据库初始化脚本 - 创建表并插入虚拟持仓数据

使用方法:
    python init_db.py

注意: 运行前请确保MySQL已启动,且在config.py中配置了正确的数据库连接信息。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from database import Base, SessionLocal, Position, RiskFactor, engine
from config import settings


# ============ 虚拟持仓数据 ============
# 标的: 中证500指数(000905.SH), 当前约5500点
# 以下为虚拟的场外衍生品持仓

SAMPLE_POSITIONS = [
    {
        "name": "中证500欧式看涨期权_1",
        "option_type": "european",
        "call_put": "call",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5600.0,
        "maturity_date": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
        "quantity": 10,
        "position_direction": "long",
        "notional": 5600000,
        "entry_price": 280000,
    },
    {
        "name": "中证500欧式看跌期权_1",
        "option_type": "european",
        "call_put": "put",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5400.0,
        "maturity_date": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
        "quantity": 10,
        "position_direction": "long",
        "notional": 5400000,
        "entry_price": 220000,
    },
    {
        "name": "中证500美式看涨期权_1",
        "option_type": "american",
        "call_put": "call",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5800.0,
        "maturity_date": (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d"),
        "quantity": 5,
        "position_direction": "long",
        "notional": 2900000,
        "entry_price": 180000,
    },
    {
        "name": "中证500美式看跌期权_1",
        "option_type": "american",
        "call_put": "put",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5200.0,
        "maturity_date": (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d"),
        "quantity": 5,
        "position_direction": "short",
        "notional": 2600000,
        "entry_price": 120000,
    },
    {
        "name": "中证500亚式算术平均看涨_1",
        "option_type": "asian",
        "call_put": "call",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5500.0,
        "maturity_date": (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d"),
        "quantity": 8,
        "position_direction": "long",
        "notional": 4400000,
        "entry_price": 200000,
        "observation_type": "arithmetic",
    },
    {
        "name": "中证500亚式几何平均看跌_1",
        "option_type": "asian",
        "call_put": "put",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5500.0,
        "maturity_date": (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d"),
        "quantity": 8,
        "position_direction": "long",
        "notional": 4400000,
        "entry_price": 180000,
        "observation_type": "geometric",
    },
    {
        "name": "中证500向上敲出看涨_1",
        "option_type": "barrier",
        "call_put": "call",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5600.0,
        "maturity_date": (datetime.now() + timedelta(days=150)).strftime("%Y-%m-%d"),
        "quantity": 6,
        "position_direction": "long",
        "notional": 3360000,
        "entry_price": 150000,
        "barrier_type": "up_and_out",
        "barrier_level": 6200.0,
    },
    {
        "name": "中证500向下敲入看跌_1",
        "option_type": "barrier",
        "call_put": "put",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5400.0,
        "maturity_date": (datetime.now() + timedelta(days=150)).strftime("%Y-%m-%d"),
        "quantity": 6,
        "position_direction": "long",
        "notional": 3240000,
        "entry_price": 90000,
        "barrier_type": "down_and_in",
        "barrier_level": 4800.0,
    },
    {
        "name": "中证500回望看涨期权_1",
        "option_type": "lookback",
        "call_put": "call",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5500.0,
        "maturity_date": (datetime.now() + timedelta(days=100)).strftime("%Y-%m-%d"),
        "quantity": 4,
        "position_direction": "long",
        "notional": 2200000,
        "entry_price": 200000,
    },
    {
        "name": "中证500回望看跌期权_1",
        "option_type": "lookback",
        "call_put": "put",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5500.0,
        "maturity_date": (datetime.now() + timedelta(days=100)).strftime("%Y-%m-%d"),
        "quantity": 4,
        "position_direction": "short",
        "notional": 2200000,
        "entry_price": 180000,
    },
    # ============ 新增奇异期权持仓 ============
    {
        "name": "中证500现金或无数字看涨_1",
        "option_type": "binary",
        "call_put": "call",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5600.0,
        "maturity_date": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
        "quantity": 20,
        "position_direction": "long",
        "notional": 11200000,
        "entry_price": 80000,
        "extra_params": '{"binary_type": "cash_or_nothing", "payoff": 1.0}',
    },
    {
        "name": "中证500资产或无数字看跌_1",
        "option_type": "binary",
        "call_put": "put",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5400.0,
        "maturity_date": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
        "quantity": 15,
        "position_direction": "long",
        "notional": 8100000,
        "entry_price": 60000,
        "extra_params": '{"binary_type": "asset_or_nothing"}',
    },
    {
        "name": "中证500选择权期权_1",
        "option_type": "chooser",
        "call_put": "call",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5500.0,
        "maturity_date": (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d"),
        "quantity": 5,
        "position_direction": "long",
        "notional": 2750000,
        "entry_price": 150000,
        "extra_params": '{"choose_time": 0.25}',
    },
    {
        "name": "中证500复合期权_CallOnCall_1",
        "option_type": "compound",
        "call_put": "call",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 200.0,
        "maturity_date": (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d"),
        "quantity": 10,
        "position_direction": "long",
        "notional": 5500000,
        "entry_price": 100000,
        "extra_params": '{"K1": 200, "K2": 5600, "T1": 0.5, "T2": 1.0, "compound_type": "call_on_call"}',
    },
    {
        "name": "中证500远期生效看涨_1",
        "option_type": "forward_start",
        "call_put": "call",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5500.0,
        "maturity_date": (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d"),
        "quantity": 8,
        "position_direction": "long",
        "notional": 4400000,
        "entry_price": 120000,
        "extra_params": '{"start_time": 0.25, "alpha": 1.0}',
    },
    {
        "name": "中证500幂期权(平方)_1",
        "option_type": "power",
        "call_put": "call",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 30000000.0,
        "maturity_date": (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d"),
        "quantity": 2,
        "position_direction": "long",
        "notional": 6050000,
        "entry_price": 200000,
        "extra_params": '{"power": 2.0}',
    },
    {
        "name": "中证500棘轮期权_1",
        "option_type": "cliquet",
        "call_put": "call",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5500.0,
        "maturity_date": (datetime.now() + timedelta(days=360)).strftime("%Y-%m-%d"),
        "quantity": 5,
        "position_direction": "long",
        "notional": 2750000,
        "entry_price": 130000,
        "extra_params": '{"n_periods": 4, "cap": 0.10, "floor": 0.0}',
    },
    {
        "name": "中证500喊价看涨期权_1",
        "option_type": "shout",
        "call_put": "call",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5600.0,
        "maturity_date": (datetime.now() + timedelta(days=150)).strftime("%Y-%m-%d"),
        "quantity": 6,
        "position_direction": "long",
        "notional": 3360000,
        "entry_price": 160000,
    },
    {
        "name": "中证500双边障碍敲出看涨_1",
        "option_type": "double_barrier",
        "call_put": "call",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5500.0,
        "maturity_date": (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d"),
        "quantity": 5,
        "position_direction": "long",
        "notional": 2750000,
        "entry_price": 90000,
        "extra_params": '{"H_lower": 4800, "H_upper": 6200, "barrier_type": "knock_out"}',
    },
    {
        "name": "中证500区间期权(区间内)_1",
        "option_type": "range",
        "call_put": "call",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5500.0,
        "maturity_date": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
        "quantity": 10,
        "position_direction": "long",
        "notional": 5500000,
        "entry_price": 50000,
        "extra_params": '{"H_lower": 5000, "H_upper": 6000, "payoff": 1.0, "range_type": "inside"}',
    },
    {
        "name": "中证500数量调整(Quanto)看涨_1",
        "option_type": "quanto",
        "call_put": "call",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5600.0,
        "maturity_date": (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d"),
        "quantity": 8,
        "position_direction": "long",
        "notional": 4480000,
        "entry_price": 140000,
        "extra_params": '{"r_f": 0.01, "sigma_fx": 0.10, "rho": 0.0}',
    },
    {
        "name": "中证500回望障碍敲出看涨_1",
        "option_type": "barrier_lookback",
        "call_put": "call",
        "underlying": "000905.SH",
        "underlying_name": "中证500指数",
        "strike": 5500.0,
        "maturity_date": (datetime.now() + timedelta(days=150)).strftime("%Y-%m-%d"),
        "quantity": 4,
        "position_direction": "long",
        "notional": 2200000,
        "entry_price": 110000,
        "extra_params": '{"strike_type": "fixed"}',
        "barrier_type": "up_and_out",
        "barrier_level": 6300.0,
    },
]


def create_database():
    """创建数据库(如果不存在)"""
    # 连接到MySQL服务器(不指定数据库)
    server_url = (
        f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/?charset=utf8mb4"
    )
    server_engine = create_engine(server_url)
    with server_engine.connect() as conn:
        conn.execute(text(
            f"CREATE DATABASE IF NOT EXISTS {settings.DB_NAME} "
            f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        ))
        conn.commit()
    server_engine.dispose()
    print(f"[1/3] 数据库 '{settings.DB_NAME}' 已就绪")


def create_tables():
    """创建所有数据表"""
    Base.metadata.create_all(bind=engine)
    print("[2/3] 数据表创建完成")


def insert_sample_data():
    """插入虚拟持仓数据"""
    db = SessionLocal()

    # 检查是否已有数据
    existing = db.query(Position).count()
    if existing > 0:
        print(f"[3/3] 已存在 {existing} 条持仓数据,跳过插入")
        db.close()
        return

    # 插入持仓
    for pos_data in SAMPLE_POSITIONS:
        pos = Position(
            name=pos_data["name"],
            option_type=pos_data["option_type"],
            call_put=pos_data["call_put"],
            underlying=pos_data["underlying"],
            underlying_name=pos_data["underlying_name"],
            strike=pos_data["strike"],
            maturity_date=datetime.strptime(pos_data["maturity_date"], "%Y-%m-%d"),
            quantity=pos_data["quantity"],
            position_direction=pos_data["position_direction"],
            notional=pos_data["notional"],
            barrier_type=pos_data.get("barrier_type"),
            barrier_level=pos_data.get("barrier_level"),
            observation_type=pos_data.get("observation_type"),
            entry_price=pos_data.get("entry_price"),
            extra_params=pos_data.get("extra_params"),
        )
        db.add(pos)

    # 插入风险因子默认值
    risk_factors = [
        RiskFactor(factor_name="中证500指数", factor_type="price", factor_code="000905.SH",
                   current_value=5500.0, unit="点", source="tushare"),
        RiskFactor(factor_name="中证500年化波动率", factor_type="volatility", factor_code="000905.SH",
                   current_value=0.25, unit="小数", source="tushare"),
        RiskFactor(factor_name="国债收益率(无风险利率)", factor_type="risk_free_rate", factor_code="10Y",
                   current_value=0.025, unit="小数", source="tushare"),
    ]
    for rf in risk_factors:
        db.add(rf)

    db.commit()
    db.close()
    print(f"[3/3] 已插入 {len(SAMPLE_POSITIONS)} 条虚拟持仓数据和 {len(risk_factors)} 条风险因子数据")


def main():
    print("=" * 60)
    print(f"  {settings.APP_NAME} - 数据库初始化")
    print("=" * 60)
    print(f"  数据库: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    print(f"  用户: {settings.DB_USER}")
    print("=" * 60)

    try:
        create_database()
        create_tables()
        insert_sample_data()
        print("\n初始化完成! 可以启动后端服务: python main.py")
    except Exception as e:
        print(f"\n初始化失败: {e}")
        print("\n请检查:")
        print("  1. MySQL服务是否已启动")
        print("  2. config.py 中的数据库配置(DB_HOST/DB_PORT/DB_USER/DB_PASSWORD)是否正确")
        print("  3. 或设置环境变量 DB_HOST, DB_PORT, DB_USER, DB_PASSWORD")
        sys.exit(1)


if __name__ == "__main__":
    main()
