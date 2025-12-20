from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import datetime

Base = declarative_base()

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    display_name = Column(String(100))
    account_type = Column(String(50), default="puter")  # puter, custom等
    status = Column(String(20), default="active")  # active, inactive, expired
    is_active = Column(Boolean, default=True)
    
    # 认证信息（加密存储）
    auth_token = Column(Text)
    refresh_token = Column(Text)
    auth_data = Column(JSON)  # 存储其他认证数据
    
    # 本地文件夹路径
    data_dir = Column(String(500))
    
    # 统计信息
    total_calls = Column(Integer, default=0)
    success_calls = Column(Integer, default=0)
    failed_calls = Column(Integer, default=0)
    last_success = Column(DateTime)
    last_failure = Column(DateTime)
    
    # 元数据
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "account_type": self.account_type,
            "status": self.status,
            "is_active": self.is_active,
            "data_dir": self.data_dir,
            "total_calls": self.total_calls,
            "success_calls": self.success_calls,
            "failed_calls": self.failed_calls,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class AppConfig(Base):
    __tablename__ = "app_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text)
    value_type = Column(String(20), default="string")  # string, json, number, boolean
    description = Column(String(500))
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            "key": self.key,
            "value": self.value,
            "value_type": self.value_type,
            "description": self.description,
        }

class BrowserSession(Base):
    __tablename__ = "browser_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    session_id = Column(String(100), unique=True, index=True)
    
    # 会话数据
    cookies = Column(JSON)
    local_storage = Column(JSON)
    session_storage = Column(JSON)
    
    # 状态
    status = Column(String(20), default="active")  # active, closed, expired
    last_used = Column(DateTime, server_default=func.now())
    
    created_at = Column(DateTime, server_default=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "session_id": self.session_id,
            "status": self.status,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }