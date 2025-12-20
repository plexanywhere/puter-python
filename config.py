import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Puter Python Manager"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # 数据库配置
    database_url: str = "sqlite+aiosqlite:///./puter.db"
    
    # 本地存储配置
    data_dir: str = "./data"
    accounts_dir: str = "./data/accounts"
    logs_dir: str = "./data/logs"
    cache_dir: str = "./data/cache"
    
    # 服务器配置
    host: str = "127.0.0.1"
    port: int = 8000
    api_key: str = "1"
    
    # Puter.js 配置
    puter_js_url: str = "https://js.puter.com/v2/"
    
    # 浏览器配置
    browser_headless: bool = False
    browser_timeout: int = 30000
    
    class Config:
        env_file = ".env"

settings = Settings()

# 创建必要的目录
def init_directories():
    directories = [
        settings.data_dir,
        settings.accounts_dir,
        settings.logs_dir,
        settings.cache_dir
    ]
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

# 初始化
init_directories()