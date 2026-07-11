"""
场外衍生品智能压力测试平台 - 后端主应用

FastAPI应用入口,整合所有API路由。
"""
import sys
import os

# 确保backend目录在Python路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from config import settings
from routes.chat import router as chat_router
from routes.positions import router as positions_router
from routes.stress_test import router as stress_test_router
from routes.market_data import router as market_data_router
from routes.rsi import router as rsi_router
from routes.pricing import router as pricing_router


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于AI的场外衍生品智能压力测试平台",
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router, prefix="/api", tags=["AI对话"])
app.include_router(positions_router, prefix="/api", tags=["持仓管理"])
app.include_router(stress_test_router, prefix="/api", tags=["压力测试"])
app.include_router(market_data_router, prefix="/api", tags=["市场数据"])
app.include_router(rsi_router, prefix="/api", tags=["RSI递归自我提升"])
app.include_router(pricing_router, prefix="/api", tags=["定价与Greeks"])


@app.on_event("startup")
async def startup():
    """应用启动时初始化数据库表"""
    try:
        init_db()
        print(f"[{settings.APP_NAME}] 数据库表初始化完成")
    except Exception as e:
        print(f"[{settings.APP_NAME}] 数据库初始化警告: {e}")
    print(f"[{settings.APP_NAME}] 服务启动完成 - http://localhost:8000")


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": settings.APP_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
