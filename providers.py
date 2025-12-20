import asyncio
import json
import time
import uuid
import logging
from typing import Dict, Any, AsyncGenerator, List, Optional
from fastapi import HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from config import settings
import sse_utils

logger = logging.getLogger(__name__)

class BaseProvider:
    async def chat_completion(
        self,
        request_data: Dict[str, Any]
    ) -> StreamingResponse:
        raise NotImplementedError
    
    async def get_models(self) -> JSONResponse:
        raise NotImplementedError

class PuterProvider(BaseProvider):
    def __init__(self):
        self.default_model = "puter-ai-model"
        self.known_models = [
            "gpt-5-nano",
            "claude-3-5-sonnet",
            "gemini-2.0-flash-exp",
            "black-forest-labs/FLUX.2-pro",
            "black-forest-labs/FLUX.2-max",
            "black-forest-labs/FLUX.1-schnell"
        ]
    
    async def chat_completion(self, request_data: Dict[str, Any]) -> StreamingResponse:
        # 模拟流式响应，实际应调用Puter.js API
        # 这里返回一个简单的模拟响应
        
        request_id = f"chatcmpl-{uuid.uuid4()}"
        model = request_data.get("model", self.default_model)
        messages = request_data.get("messages", [])
        user_message = messages[-1].get("content") if messages else "Hello"
        
        # 检查是否流式传输
        stream = request_data.get("stream", False)
        
        if stream:
            async def stream_generator() -> AsyncGenerator[bytes, None]:
                # 模拟思考过程
                response_text = f"这是通过Puter.js AI模型 '{model}' 生成的模拟响应。用户说: {user_message}"
                words = response_text.split()
                for word in words:
                    chunk = sse_utils.create_chat_completion_chunk(request_id, model, word + " ")
                    yield sse_utils.create_sse_data(chunk)
                    await asyncio.sleep(0.05)
                
                final_chunk = sse_utils.create_chat_completion_chunk(request_id, model, "", "stop")
                yield sse_utils.create_sse_data(final_chunk)
                yield sse_utils.DONE_CHUNK
            
            return StreamingResponse(stream_generator(), media_type="text/event-stream")
        else:
            # 非流式响应
            response_text = f"这是通过Puter.js AI模型 '{model}' 生成的模拟响应。用户说: {user_message}"
            response_data = sse_utils.create_chat_completion_response(request_id, model, response_text)
            return JSONResponse(content=response_data)
    
    async def get_models(self) -> JSONResponse:
        model_data = {
            "object": "list",
            "data": [
                {
                    "id": name,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "puter"
                }
                for name in self.known_models
            ]
        }
        return JSONResponse(content=model_data)

# 全局提供者实例
provider = PuterProvider()