"""
场外衍生品智能压力测试平台 - 全局配置
"""
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "场外衍生品智能压力测试平台"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库配置
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "123456")
    DB_NAME: str = os.getenv("DB_NAME", "derivatives_stress_test")

    # 智谱AI配置
    ZHIPU_API_KEY: str = "325d6fa364954d2e871c30ba95b553bd.KBdQdqgJgELJBhnv"
    ZHIPU_MODEL: str = "glm-4.5-flash"

    # Tushare配置
    TUSHARE_TOKEN: str = "cd854e5eec6ac50c8ead11982f5333bf61345a847399d62c63c42776"

    # 标的资产配置 - 中证500指数
    UNDERLYING_INDEX: str = "000905.SH"
    UNDERLYING_NAME: str = "中证500指数"

    # 前端CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )


settings = Settings()
