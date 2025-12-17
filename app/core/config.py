"""
应用配置模块

使用 pydantic-settings 管理环境变量和应用配置
"""
from functools import lru_cache
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
import json

# 项目根目录 (HRM2-Vue-FastAPI-Backend)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """应用配置类"""
    
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # 应用基础配置
    app_name: str = "HRM2-API"
    app_env: str = "development"
    debug: bool = True
    
    # 数据库配置
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'hrm2.db'}"
    
    # CORS 配置
    cors_origins: List[str] = ["*"]
    
    # LLM 配置
    llm_model: str = "deepseek-chat"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_temperature: float = 0.7
    llm_timeout: int = 120
    llm_max_concurrency: int = 5
    llm_rate_limit: int = 60
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("database_url", mode="before")
    @classmethod
    def fix_database_path(cls, v):
        if isinstance(v, str) and "./data/" in v:
            return v.replace("./data/", str(BASE_DIR / "data") + "/")
        return v
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.app_env == "development"
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 全局配置实例
settings = get_settings()
