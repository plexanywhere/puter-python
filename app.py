import asyncio
import platform
import sys

# 解决 Windows 上 Playwright 的 NotImplementedError 问题
# 必须在任何其他导入之前设置，特别是 asyncio 被隐式使用之前
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from sqlalchemy.orm import Session
import logging
import uvicorn
import json
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from typing import List, Dict, Any
from puter_bridge import PuterBridge
from pathlib import Path
from config import settings
from database import get_db, create_tables
from models import Account, AppConfig, BrowserSession
import schemas
import services
import providers

app = FastAPI(title=settings.app_name, version=settings.app_version)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
static_dir = Path("./static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 初始化数据库
create_tables()

# 确保数据目录存在
from config import settings
for dir_path in [settings.data_dir, settings.accounts_dir, settings.logs_dir, settings.cache_dir]:
    Path(dir_path).mkdir(parents=True, exist_ok=True)

# 首页
@app.get("/", response_class=HTMLResponse)
async def root():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Puter Python Manager</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; }
            .links { margin-top: 30px; }
            .link { display: inline-block; margin-right: 15px; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
            .link:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Puter Python Manager</h1>
            <p>本地Python可视化软件，集成Puter.js AI功能和多账号管理。</p>
            <div class="links">
                <a class="link" href="/puter-app">启动 Puter AI 应用</a>
                <a class="link" href="/admin">管理控制台</a>
                <a class="link" href="/docs">API文档</a>
                <a class="link" href="/redoc">ReDoc文档</a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# 管理控制台页面
@app.get("/admin", response_class=HTMLResponse)
async def admin_console():
    # 返回管理界面的HTML
    static_index_path = Path("./static/index.html")
    if static_index_path.exists():
        return HTMLResponse(content=static_index_path.read_text(encoding="utf-8"))
    else:
        return HTMLResponse(content="<h1>管理控制台</h1><p>页面建设中...</p>")

# Puter.js 前端应用
@app.get("/puter-app", response_class=HTMLResponse)
async def puter_app():
    return FileResponse("static/app.html")

# 系统信息API
@app.get("/api/system/info")
def system_info():
    import platform
    import sys
    from datetime import datetime
    
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.platform(),
        "host_name": platform.node(),
        "working_dir": os.getcwd(),
        "uptime": datetime.now().isoformat(),  # 简化，实际应记录启动时间
        "data_dir": settings.data_dir,
    }

# 系统状态API
@app.get("/api/system/status")
def system_status(db: Session = Depends(get_db)):
    from sqlalchemy import func
    
    # 账号统计
    total_accounts = db.query(func.count(Account.id)).scalar() or 0
    active_accounts = db.query(func.count(Account.id)).filter(Account.is_active == True).scalar() or 0
    
    # 配置统计
    total_configs = db.query(func.count(AppConfig.id)).scalar() or 0
    
    # 会话统计
    active_sessions = db.query(func.count(BrowserSession.id)).filter(BrowserSession.status == "active").scalar() or 0
    
    # 内存使用（简化）
    import psutil
    memory_percent = psutil.virtual_memory().percent
    
    return {
        "service_status": "running",
        "botasaurus_status": "initialized",
        "total_accounts": total_accounts,
        "active_accounts": active_accounts,
        "total_configs": total_configs,
        "active_sessions": active_sessions,
        "memory_usage": memory_percent,
        "api_requests": 0,  # 可扩展：记录请求计数
    }

# API密钥验证依赖
async def verify_api_key(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    api_key = services.ConfigService.get_config(db, key="api_key")
    if api_key and api_key != "1":  # 如果配置了API密钥且不是默认值
        if not authorization or "bearer" not in authorization.lower():
            raise HTTPException(status_code=401, detail="需要 Bearer Token 认证")
        token = authorization.split(" ")[-1]
        if token != api_key:
            raise HTTPException(status_code=403, detail="无效的 API Key")

# OpenAI兼容API端点
@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    db: Session = Depends(get_db)
):
    await verify_api_key(request.headers.get("Authorization"), db)
    try:
        request_data = await request.json()
        token = services.AccountService.get_next_token(db)
        if not token:
             raise HTTPException(status_code=400, detail="未找到活跃的 Puter 账号。请先在管理后台连接账号。")

        return StreamingResponse(
            PuterBridge.chat_completion_stream(request_data, token),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"处理聊天请求错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/models")
async def list_models(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    await verify_api_key(authorization, db)
    await verify_api_key(authorization, db)
    return PuterBridge.get_models()

# 健康检查
@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": __import__("datetime").datetime.now().isoformat()}

# 账号管理API
@app.get("/api/accounts")
def list_accounts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    accounts = services.AccountService.list_accounts(db, skip=skip, limit=limit)
    return {
        "success": True,
        "accounts": [account.to_dict() for account in accounts],
        "total": len(accounts)
    }

@app.get("/api/accounts/{account_id}")
async def get_account(account_id: int, db: Session = Depends(get_db)):
    account = services.AccountService.get_account(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    return {"success": True, "account": account.to_dict()}

@app.post("/api/accounts")
async def create_account(account_data: schemas.AccountCreate, db: Session = Depends(get_db)):
    try:
        account = services.AccountService.create_account(db, account_data)
        return {
            "success": True,
            "message": "账号创建成功",
            "account": account.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/account/create")
async def create_account_compat(account_data: schemas.AccountCreate, db: Session = Depends(get_db)):
    """
    前端兼容性端点 - 重定向到/api/accounts
    """
    try:
        account = services.AccountService.create_account(db, account_data)
        return {
            "success": True,
            "message": "账号创建成功",
            "account": account.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/account/{id}/bind")
async def bind_account(id: int, request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        account = services.AccountService.bind_account(db, id, data)
        if not account:
            return JSONResponse({"success": False, "message": "账号不存在"})
        return JSONResponse({"success": True, "account_name": account.name})
    except Exception as e:
        logger.error(f"Bind account failed: {e}")
        return JSONResponse({"success": False, "message": str(e)})

@app.post("/api/account/{account_id}/launch-browser")
async def launch_browser_for_account_compat(
    account_id: int,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    前端兼容性端点 - 启动浏览器进行账号登录
    """
    account = services.AccountService.get_account(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    
    # 在后台启动浏览器登录流程
    background_tasks.add_task(
        services.BrowserService.launch_browser_for_account,
        account
    )
    
    return {
        "success": True,
        "message": f"已启动浏览器登录流程: {account.name}",
        "account_name": account.name
    }

@app.delete("/api/account/{account_id}")
async def delete_account_compat(account_id: int, db: Session = Depends(get_db)):
    """
    前端兼容性端点 - 重定向到/api/accounts/{account_id}
    """
    success = services.AccountService.delete_account(db, account_id)
    if not success:
        raise HTTPException(status_code=404, detail="账号不存在")
    return {"success": True, "message": "账号删除成功"}

@app.put("/api/accounts/{account_id}")
async def update_account(
    account_id: int,
    update_data: schemas.AccountUpdate,
    db: Session = Depends(get_db)
):
    account = services.AccountService.update_account(db, account_id, update_data)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    return {
        "success": True,
        "message": "账号更新成功",
        "account": account.to_dict()
    }

@app.delete("/api/accounts/{account_id}")
async def delete_account(account_id: int, db: Session = Depends(get_db)):
    success = services.AccountService.delete_account(db, account_id)
    if not success:
        raise HTTPException(status_code=404, detail="账号不存在")
    return {"success": True, "message": "账号删除成功"}

@app.post("/api/account/login/start")
async def start_account_login(
    name: str = "新账号",
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    # 创建账号（如果不存在）
    account = services.AccountService.get_account_by_name(db, name)
    if not account:
        account_data = schemas.AccountCreate(name=name, display_name=name)
        account = services.AccountService.create_account(db, account_data)
    
    # 在后台启动浏览器登录流程
    background_tasks.add_task(
        services.BrowserService.launch_browser_for_account,
        account
    )
    
    return {
        "success": True,
        "message": f"已启动账号登录流程: {account.name}",
        "account": account.to_dict()
    }

@app.get("/api/accounts/{account_id}/data")
async def get_account_data(account_id: int, db: Session = Depends(get_db)):
    account = services.AccountService.get_account(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    
    data = services.BrowserService.load_account_data(account)
    return {
        "success": True,
        "account": account.name,
        "data": data
    }

# 配置管理API
@app.get("/api/configs")
async def list_configs(db: Session = Depends(get_db)):
    configs = services.ConfigService.list_configs(db)
    return {
        "success": True,
        "configs": [config.to_dict() for config in configs]
    }

@app.get("/api/configs/{key}")
async def get_config(key: str, db: Session = Depends(get_db)):
    value = services.ConfigService.get_config(db, key)
    if value is None:
        raise HTTPException(status_code=404, detail="配置不存在")
    return {"success": True, "key": key, "value": value}

@app.post("/api/configs")
async def set_config(
    config_data: schemas.ConfigCreate,
    db: Session = Depends(get_db)
):
    config = services.ConfigService.set_config(
        db,
        config_data.key,
        config_data.value,
        config_data.value_type,
        config_data.description
    )
    return {
        "success": True,
        "message": "配置设置成功",
        "config": config.to_dict()
    }

@app.delete("/api/configs/{key}")
async def delete_config(key: str, db: Session = Depends(get_db)):
    success = services.ConfigService.delete_config(db, key)
    if not success:
        raise HTTPException(status_code=404, detail="配置不存在")
    return {"success": True, "message": "配置删除成功"}

# AI功能API
@app.post("/api/ai/chat")
async def ai_chat(chat_request: schemas.ChatRequest, db: Session = Depends(get_db)):
    result = await services.AIService.chat(
        db,
        chat_request.message,
        chat_request.model,
        chat_request.stream
    )
    return {"success": True, "result": result}

@app.post("/api/ai/generate-image")
async def generate_image(image_request: schemas.ImageGenerationRequest, db: Session = Depends(get_db)):
    result = await services.AIService.generate_image(
        db,
        image_request.prompt,
        image_request.model,
        width=image_request.width,
        height=image_request.height,
        steps=image_request.steps,
        seed=image_request.seed,
        disable_safety_checker=image_request.disable_safety_checker
    )
    return {"success": True, "result": result}

# Cookie解析API
@app.post("/api/cookie/parse")
async def parse_cookie(
    request: schemas.CookieParseRequest,
    db: Session = Depends(get_db)
):
    # 简单解析示例，实际应实现更复杂的解析逻辑
    try:
        # 检查是否是JSON格式
        import json
        cookie_data = json.loads(request.text)
        cookie_text = json.dumps(cookie_data, indent=2)
    except:
        cookie_text = request.text
    
    # 创建账号
    account_name = request.account_name or "导入的账号"
    account = services.AccountService.get_account_by_name(db, account_name)
    if not account:
        account_data = schemas.AccountCreate(
            name=account_name,
            display_name=account_name,
            account_type="custom"
        )
        account = services.AccountService.create_account(db, account_data)
    
    # 保存cookie数据
    account_dir = Path(account.data_dir)
    cookie_file = account_dir / "cookies" / "parsed_cookies.txt"
    cookie_file.write_text(cookie_text, encoding="utf-8")
    
    return {
        "success": True,
        "message": f"Cookie已解析并保存到账号: {account.name}",
        "account": account.to_dict()
    }

# 前端兼容性API - 系统状态
@app.get("/api/system")
async def get_system_status():
    """
    获取系统状态信息 - 前端兼容性端点
    """
    return {
        "success": True,
        "status": "running",
        "version": "1.0.0",
        "uptime": "0 days",
        "timestamp": datetime.now().isoformat()
    }

# 前端兼容性API - 配置信息
@app.get("/api/config")
async def get_config_compat(db: Session = Depends(get_db)):
    """
    获取配置信息 - 前端兼容性端点
    返回系统配置和设置
    """
    # 获取浏览器配置
    browser_headless = services.ConfigService.get_config(db, "browser_headless")
    browser_timeout = services.ConfigService.get_config(db, "browser_timeout")
    
    return {
        "success": True,
        "config": {
            "browser": {
                "headless": browser_headless if browser_headless is not None else True,
                "timeout": int(browser_timeout) if browser_timeout is not None else 30
            },
            "system": {
                "auto_save": True,
                "debug_mode": settings.debug
            }
        }
    }

# 前端兼容性API - 获取所有账号列表
@app.get("/api/accounts")
async def list_accounts_compat(db: Session = Depends(get_db)):
    """
    获取所有账号列表 - 前端兼容性端点
    """
    accounts = services.AccountService.list_accounts(db)
    return {
        "success": True,
        "accounts": [account.to_dict() for account in accounts]
    }

# 前端兼容性API - 设置配置
@app.post("/api/config/set")
async def set_config_compat(config_data: dict, db: Session = Depends(get_db)):
    """
    设置配置信息 - 前端兼容性端点
    """
    try:
        key = config_data.get("key")
        value = config_data.get("value")
        value_type = config_data.get("value_type", "string")
        description = config_data.get("description", "")
        
        if not key or value is None:
            raise HTTPException(status_code=400, detail="Missing key or value")
        
        services.ConfigService.set_config(db, key, str(value), value_type, description)
        
        return {
            "success": True,
            "message": f"配置 {key} 已更新"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 前端兼容性API - 重启系统
@app.post("/api/system/restart")
async def restart_system():
    """
    重启系统 - 前端兼容性端点
    注意：在实际部署中，这可能需要更复杂的处理
    """
    try:
        # 在实际应用中，这里应该执行真正的重启逻辑
        # 对于开发环境，我们只是返回成功消息
        import os
        import sys
        
        # 重启Uvicorn服务器的简单方法
        # 注意：这在生产环境中可能需要更复杂的处理
        def restart():
            os.execv(sys.executable, [sys.executable] + sys.argv)
        
        # 使用异步方式延迟重启，确保响应能够返回
        import asyncio
        loop = asyncio.get_event_loop()
        loop.call_later(1, restart)
        
        return {
            "success": True,
            "message": "系统将在1秒后重启"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 启动服务器
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=False, # Windows 上使用 Playwright 时必须禁用 reload，否则会因多进程导致 NotImplementedError
        workers=1
    )