from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

# 基础模型
class BaseResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None

# 账号相关模型
class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = None
    account_type: str = "puter"
    auth_token: Optional[str] = None
    auth_data: Optional[Dict[str, Any]] = None

class AccountUpdate(BaseModel):
    display_name: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    auth_token: Optional[str] = None
    auth_data: Optional[Dict[str, Any]] = None

class AccountResponse(BaseModel):
    id: int
    name: str
    display_name: Optional[str]
    account_type: str
    status: str
    is_active: bool
    data_dir: Optional[str]
    total_calls: int
    success_calls: int
    failed_calls: int
    last_success: Optional[datetime]
    last_failure: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# 配置相关模型
class ConfigCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    value: str
    value_type: str = "string"
    description: Optional[str] = None

class ConfigUpdate(BaseModel):
    value: Optional[str] = None
    value_type: Optional[str] = None
    description: Optional[str] = None

class ConfigResponse(BaseModel):
    key: str
    value: str
    value_type: str
    description: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# 浏览器会话相关模型
class BrowserSessionCreate(BaseModel):
    account_id: int
    cookies: Optional[Dict[str, Any]] = None
    local_storage: Optional[Dict[str, Any]] = None
    session_storage: Optional[Dict[str, Any]] = None

class BrowserSessionResponse(BaseModel):
    id: int
    account_id: int
    session_id: str
    status: str
    last_used: Optional[datetime]
    created_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# 认证相关模型
class PuterAuthRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    auth_token: Optional[str] = None

class CookieParseRequest(BaseModel):
    text: str
    account_name: Optional[str] = "导入的账号"

# 系统状态模型
class SystemStatusResponse(BaseModel):
    service_status: str
    botasaurus_status: str
    total_accounts: int
    active_accounts: int
    total_configs: int
    active_sessions: int
    memory_usage: float
    api_requests: int

# AI请求模型
class ChatRequest(BaseModel):
    message: str
    model: str = "gpt-5-nano"
    stream: bool = False

class ImageGenerationRequest(BaseModel):
    prompt: str
    model: str = "black-forest-labs/FLUX.2-pro"
    width: Optional[int] = 512
    height: Optional[int] = 512
    steps: Optional[int] = 30
    seed: Optional[int] = None
    disable_safety_checker: bool = True