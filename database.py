from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings
import os

# 同步引擎（用于迁移等）
engine = create_engine(
    settings.database_url.replace("+aiosqlite", ""),  # 移除异步前缀
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 依赖项
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 创建表
def create_tables():
    from models import Base
    Base.metadata.create_all(bind=engine)

# 初始化数据库
if not os.path.exists("./puter.db"):
    create_tables()
    print("数据库表已创建")