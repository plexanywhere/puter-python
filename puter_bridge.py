import json
import httpx
import time
import logging
import asyncio
from typing import List, Dict, Any, AsyncGenerator, Optional

logger = logging.getLogger(__name__)

class PuterBridge:
    UPSTREAM_URL = "https://api.puter.com/drivers/call"
    
    # 从JS配置中移植的模型列表
    CHAT_MODELS = [
        "gpt-4o-mini", "gpt-4o", "claude-3-5-sonnet",
        "gemini-2.0-flash", "deepseek-chat", "deepseek-reasoner",
        "gpt-4o-2024-11-20", "o1", "o1-mini", "o1-pro", "o3-mini",
        "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
        "claude-3-7-sonnet-20250219", "claude-3-7-sonnet-latest",
        "gemini-2.0-flash-lite-001", "gemini-2.0-flash-001",
        "grok-2", "grok-2-vision", "grok-3", "grok-3-mini",
        "mistral-large-latest", "mistral-small-latest",
        "qwen-2.5-72b-instruct", "qwen-2.5-coder-32b-instruct",
        "llama-3.1-405b-instruct", "llama-3.3-70b-instruct"
    ]
    
    IMAGE_MODELS = ["gpt-image-1"]
    
    DEFAULT_CHAT_MODEL = "gpt-4o-mini"
    DEFAULT_IMAGE_MODEL = "gpt-image-1"

    @staticmethod
    def _get_driver_from_model(model: str) -> str:
        if model.startswith(("gpt", "o1", "o3", "o4")): return "openai-completion"
        if model.startswith("claude"): return "claude"
        if model.startswith("gemini"): return "gemini"
        if model.startswith("grok"): return "xai"
        return "openai-completion"

    @staticmethod
    def _create_upstream_headers() -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Origin": "https://docs.puter.com",
            "Referer": "https://docs.puter.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    @classmethod
    async def chat_completion_stream(cls, request_data: Dict[str, Any], token: str) -> AsyncGenerator[str, None]:
        if not token:
            yield f"data: {json.dumps({'error': 'No available account token'})}\n\n"
            return

        model = request_data.get("model", cls.DEFAULT_CHAT_MODEL)
        payload = {
            "interface": "puter-chat-completion",
            "driver": cls._get_driver_from_model(model),
            "test_mode": False,
            "method": "complete",
            "args": {
                "messages": request_data.get("messages", []),
                "model": model,
                "stream": True
            },
            "auth_token": token
        }

        async with httpx.AsyncClient() as client:
            try:
                async with client.stream("POST", cls.UPSTREAM_URL, json=payload, headers=cls._create_upstream_headers(), timeout=60.0) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"Upstream error: {response.status_code} - {error_text}")
                        yield f"data: {json.dumps({'error': f'Upstream error: {response.status_code}'})}\n\n"
                        return

                    async for line in response.aiter_lines():
                        if not line or not line.strip():
                            continue
                        
                        try:
                            # Puter returns raw JSON streams (NDJSON), not SSE "data: ..." format
                            data = json.loads(line)
                            logger.info(f"Puter Raw Chunk: {data}")
                            
                            # Handle upstream errors (e.g. Model not found)
                            if isinstance(data, dict) and (data.get("error") or data.get("success") is False):
                                error_msg = data.get("error", "Unknown upstream error")
                                logger.error(f"Puter API Error: {error_msg}")
                                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                                return

                            if data.get("type") == "text" and isinstance(data.get("text"), str):
                                chunk = {
                                    "id": f"chatcmpl-{int(time.time())}",
                                    "object": "chat.completion.chunk",
                                    "created": int(time.time()),
                                    "model": model,
                                    "choices": [{
                                        "index": 0,
                                        "delta": {"content": data["text"]},
                                        "finish_reason": None
                                    }]
                                }
                                yield f"data: {json.dumps(chunk)}\n\n"
                        except json.JSONDecodeError:
                            continue
                    
                    # End of stream
                    final_chunk = {
                        "id": f"chatcmpl-{int(time.time())}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }]
                    }
                    yield f"data: {json.dumps(final_chunk)}\n\n"
                    yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

    @classmethod
    async def chat_completion(cls, request_data: Dict[str, Any], token: str) -> Dict[str, Any]:
        # Non-streaming implementation (wraps internal call)
        # For simplicity, we can reuse the stream generator or implement a separate call
        # But Puter API seems to favor streaming in the referenced JS code (stream: true is hardcoded in JS payload helper for chat)
        # So we'll accumulate the stream.
        
        full_content = ""
        model = request_data.get("model", cls.DEFAULT_CHAT_MODEL)
        
        async for chunk_str in cls.chat_completion_stream(request_data, token):
            if chunk_str.startswith("data: ") and not chunk_str.strip().endswith("[DONE]"):
                try:
                    chunk_json = json.loads(chunk_str[6:])
                    if "choices" in chunk_json:
                        delta = chunk_json["choices"][0].get("delta", {})
                        full_content += delta.get("content", "")
                except:
                    pass
        
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": full_content
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0, # Calculation would require tokenizer
                "total_tokens": 0
            }
        }

    @classmethod
    async def generate_image(cls, request_data: Dict[str, Any], token: str) -> Dict[str, Any]:
        if not token:
            raise ValueError("No available account token")

        model = request_data.get("model", cls.DEFAULT_IMAGE_MODEL)
        payload = {
            "interface": "puter-image-generation",
            "driver": "openai-image-generation",
            "test_mode": False,
            "method": "generate",
            "args": {
                "model": model,
                "quality": request_data.get("quality", "high"),
                "prompt": request_data.get("prompt")
            },
            "auth_token": token
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(cls.UPSTREAM_URL, json=payload, headers=cls._create_upstream_headers(), timeout=120.0)
            
            if response.status_code != 200:
                raise Exception(f"Upstream error: {response.status_code} - {response.text}")
            
            # Puter returns raw binary image data
            import base64
            b64_json = base64.b64encode(response.content).decode('utf-8')
            
            return {
                "created": int(time.time()),
                "data": [{"b64_json": b64_json}]
            }

    @classmethod
    def get_models(cls) -> Dict[str, Any]:
        all_models = cls.CHAT_MODELS + cls.IMAGE_MODELS
        return {
            "object": "list",
            "data": [
                {
                    "id": m,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "puter-bridge"
                } for m in all_models
            ]
        }
