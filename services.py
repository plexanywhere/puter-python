import os
import json
import shutil
import asyncio
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging
from typing import Optional, Dict, Any, List

from config import settings
from models import Account, AppConfig, BrowserSession
from puter_bridge import PuterBridge
import schemas
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 账号服务
class AccountService:
    @staticmethod
    def create_account(db: Session, account_data: schemas.AccountCreate) -> Account:
        # 创建账号文件夹
        account_dir_name = f"账号{db.query(Account).count() + 1:03d}"
        account_dir = Path(settings.accounts_dir) / account_dir_name
        account_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建账号数据文件夹结构
        (account_dir / "cookies").mkdir(exist_ok=True)
        (account_dir / "cache").mkdir(exist_ok=True)
        (account_dir / "logs").mkdir(exist_ok=True)
        (account_dir / "data").mkdir(exist_ok=True)
        
        # 创建账号记录
        account = Account(
            name=account_data.name,
            display_name=account_data.display_name or account_data.name,
            account_type=account_data.account_type,
            data_dir=str(account_dir.absolute()),
            auth_token=account_data.auth_token,
            auth_data=account_data.auth_data
        )
        
        try:
            db.add(account)
            db.commit()
            db.refresh(account)
            logger.info(f"账号创建成功: {account.name}")
            return account
        except IntegrityError:
            db.rollback()
            raise ValueError(f"账号名称已存在: {account_data.name}")
    
    @staticmethod
    def get_account(db: Session, account_id: int) -> Optional[Account]:
        return db.query(Account).filter(Account.id == account_id).first()
    
    @staticmethod
    def get_account_by_name(db: Session, name: str) -> Optional[Account]:
        return db.query(Account).filter(Account.name == name).first()
    
    @staticmethod
    def list_accounts(db: Session, skip: int = 0, limit: int = 100) -> List[Account]:
        return db.query(Account).offset(skip).limit(limit).all()
    
    @staticmethod
    def update_account(db: Session, account_id: int, update_data: schemas.AccountUpdate) -> Optional[Account]:
        account = AccountService.get_account(db, account_id)
        if not account:
            return None
        
        for key, value in update_data.dict(exclude_unset=True).items():
            setattr(account, key, value)
        
        db.commit()
        db.refresh(account)
        return account
    
    @staticmethod
    def delete_account(db: Session, account_id: int) -> bool:
        account = AccountService.get_account(db, account_id)
        if not account:
            return False
        
        # 删除本地文件夹
        if account.data_dir and Path(account.data_dir).exists():
            shutil.rmtree(account.data_dir, ignore_errors=True)
        
        db.delete(account)
        db.commit()
        return True
    
    @staticmethod
    def update_account_stats(db: Session, account_id: int, success: bool = True):
        account = AccountService.get_account(db, account_id)
        if not account:
            return
        
        account.total_calls += 1
        if success:
            account.success_calls += 1
            account.last_success = __import__("datetime").datetime.now()
        else:
            account.failed_calls += 1
            account.last_failure = __import__("datetime").datetime.now()
        
        db.commit()

    @staticmethod
    def bind_account(db: Session, account_id: int, puter_user_data: Dict[str, Any]) -> Optional[Account]:
        account = AccountService.get_account(db, account_id)
        if not account:
            return None
            
        # 更新账号状态
        account.is_active = True
        account.status = "active"
        account.last_success = __import__("datetime").datetime.now()
        
        # 更新认证数据
        current_auth_data = account.auth_data or {}
        current_auth_data.update({
            "puter_user": puter_user_data,
            "bound_at": __import__("datetime").datetime.now().isoformat(),
            "source": "puter.js_sdk"
        })
        account.auth_data = current_auth_data
        
        if puter_user_data.get("username"):
            account.display_name = puter_user_data.get("username")
            
        # 尝试保存Token如果存在
        if puter_user_data.get("token"):
             account.auth_token = puter_user_data.get("token")

        db.commit()
        db.refresh(account)
        return account

    @staticmethod
    def get_next_token(db: Session) -> Optional[str]:
        # 获取所有活跃且有Token的账号
        accounts = db.query(Account).filter(
            Account.status == "active",
            Account.auth_token != None,
            Account.auth_token != ""
        ).all()
        
        if not accounts:
            return None
            
        # 简单随机轮询
        account = random.choice(accounts)
        return account.auth_token

# 配置服务
class ConfigService:
    @staticmethod
    def get_config(db: Session, key: str) -> Optional[str]:
        config = db.query(AppConfig).filter(AppConfig.key == key).first()
        return config.value if config else None
    
    @staticmethod
    def set_config(db: Session, key: str, value: str, value_type: str = "string", description: str = ""):
        config = db.query(AppConfig).filter(AppConfig.key == key).first()
        if config:
            config.value = value
            config.value_type = value_type
            config.description = description
        else:
            config = AppConfig(key=key, value=value, value_type=value_type, description=description)
            db.add(config)
        db.commit()
        return config
    
    @staticmethod
    def list_configs(db: Session) -> List[AppConfig]:
        return db.query(AppConfig).all()
    
    @staticmethod
    def delete_config(db: Session, key: str) -> bool:
        config = db.query(AppConfig).filter(AppConfig.key == key).first()
        if not config:
            return False
        db.delete(config)
        db.commit()
        return True

# 浏览器自动化服务
class BrowserService:
    @staticmethod
    async def launch_browser_for_account(account: Account):
        # [Deprecated] 浏览器自动化已弃用，改用前端 Puter.js 直接登录
        logger.warning(f"Backend browser launch deprecated for account: {account.name}")
        return {
            "success": False, 
            "message": "Backend browser automation is deprecated. Please use the frontend 'Connect Puter' button."
        }
    
    @staticmethod
    def load_account_data(account: Account) -> Dict[str, Any]:
        account_dir = Path(account.data_dir)
        data = {}
        
        # 加载cookies
        cookies_file = account_dir / "cookies" / "cookies.json"
        if cookies_file.exists():
            try:
                data["cookies"] = json.loads(cookies_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"加载cookies失败: {e}")
                data["cookies"] = []
        
        # 加载storage
        storage_file = account_dir / "cookies" / "storage.json"
        if storage_file.exists():
            try:
                storage_data = json.loads(storage_file.read_text(encoding="utf-8"))
                data["local_storage"] = storage_data.get("local_storage", {})
                data["session_storage"] = storage_data.get("session_storage", {})
            except Exception as e:
                logger.error(f"加载storage失败: {e}")
                data["local_storage"] = {}
                data["session_storage"] = {}
        
        return data

# AI服务（集成Puter.js）
class AIService:
    @staticmethod
    async def generate_image(db: Session, prompt: str, model: str = "gpt-image-1", **kwargs):
        token = AccountService.get_next_token(db)
        if not token:
             return {"error": "No active account found. Please connect a Puter account first."}
             
        try:
             return await PuterBridge.generate_image({
                 "prompt": prompt,
                 "model": model, 
                 "quality": kwargs.get("quality", "high")
             }, token)
        except Exception as e:
             logger.error(f"Image generation failed: {e}")
             return {"error": str(e)}
    
    @staticmethod
    async def chat(db: Session, message: str, model: str = "gpt-4o-mini", stream: bool = False):
        # 注意: 这里的chat方法主要用于简单的内部测试或非流式调用
        # 流式调用应该直接在API层处理
        
        token = AccountService.get_next_token(db)
        if not token:
             return {"error": "No active account found. Please connect a Puter account first."}

        try:
             return await PuterBridge.chat_completion({
                 "messages": [{"role": "user", "content": message}],
                 "model": model
             }, token)
        except Exception as e:
             logger.error(f"Chat completion failed: {e}")
             return {"error": str(e)}

# 初始化默认配置
def init_default_configs(db: Session):
    default_configs = [
        ("api_key", "1", "string", "API访问密钥"),
        ("host", settings.host, "string", "服务器主机"),
        ("port", str(settings.port), "string", "服务器端口"),
        ("puter_js_url", settings.puter_js_url, "string", "Puter.js库URL"),
        ("browser_headless", str(settings.browser_headless), "boolean", "浏览器无头模式"),
    ]
    
    for key, value, value_type, description in default_configs:
        ConfigService.set_config(db, key, value, value_type, description)