import requests
import json
from typing import Optional
from datetime import datetime
import base64
import aiohttp
import asyncio
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MicrosoftTranslator:
    def __init__(self, timeout: int = 60, pre_expiration: int = 120, default_expiration: int = 600):
        self.auth_url = "https://edge.microsoft.com/translate/auth"
        self.translate_url = "https://api.cognitive.microsofttranslator.com/translate"
        self.timeout = timeout
        self.pre_expiration = pre_expiration
        self.default_expiration = default_expiration
        self.access_token = None
        self.expire_at = -1
        # 创建持久的requests会话
        self.session = requests.Session()
        # 初始化aiohttp持久会话
        self.aiohttp_session = None  # 延迟初始化

    def update_access_token(self, token: str):
        expiration_time = self.get_expiration_time_from_token(token)
        logger.info(f"Access token updated. Expires at: {datetime.fromtimestamp(expiration_time)}")
        self.access_token = token
        self.expire_at = expiration_time - self.pre_expiration

    def get_expiration_time_from_token(self, token: str) -> float:
        try:
            payload_chunk = token.split('.')[1]
            # 如果需要，添加填充
            padding = '=' * (-len(payload_chunk) % 4)
            payload = json.loads(base64.b64decode(payload_chunk + padding).decode("utf-8"))
            expiration_time = payload.get("exp")
            if not expiration_time:
                raise ValueError("Token payload 中未找到过期时间。")
            return expiration_time
        except (IndexError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"解析token payload失败: {e}")
            return datetime.now().timestamp() + self.default_expiration - (self.pre_expiration / 2)

    def get_access_token(self) -> str:
        if self.access_token and datetime.now().timestamp() < self.expire_at:
            return self.access_token

        try:
            response = self.session.get(  # 使用持久会话
                self.auth_url,
                headers={
                    "Accept": "*/*",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0"
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            token = response.text.strip()
            if not token:
                raise ValueError("从认证端点接收到空token。")
            self.update_access_token(token)
            return token
        except requests.RequestException as e:
            logger.error(f"认证失败: {e}")
            raise RuntimeError("获取access token失败。") from e

    def translate(self, text: str, from_lang: str, to_lang: str, text_type: str = "PLAIN") -> Optional[str]:
        translate_params = {
            "api-version": "3.0",
            "from": from_lang,
            "to": to_lang,
            "textType": text_type
        }
        translate_headers = {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json"
        }
        translate_payload = [{"text": text}]

        try:
            response = self.session.post(  # 使用持久会话
                self.translate_url,
                params=translate_params,
                json=translate_payload,
                headers=translate_headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            translation = response.json()

            logger.debug(f"Request URL: {response.request.url}")
            logger.debug(f"Request Headers: {response.request.headers}")
            logger.debug(f"Request Body: {response.request.body}")
            logger.info(f"Response Status Code: {response.status_code}")
            logger.debug(f"Response Body: {response.text}")

            return translation[0]["translations"][0]["text"]
        except requests.HTTPError as e:
            logger.error(f"翻译过程中发生HTTP错误: {e}")
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"解析翻译响应时出错: {e}")
        except requests.RequestException as e:
            logger.error(f"翻译请求失败: {e}")
        return None

    # 异步翻译
    async def translate_async(self, text: str, from_lang: str, to_lang: str, text_type: str = "PLAIN") -> Optional[str]:
        if from_lang == "auto":
            from_lang = ""
        translate_params = {
            "api-version": "3.0",
            "from": from_lang,
            "to": to_lang,
            "textType": text_type
        }
        translate_headers = {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json"
        }
        translate_payload = [{"text": text}]

        # 确保aiohttp会话已初始化
        if not self.aiohttp_session:
            self.aiohttp_session = aiohttp.ClientSession()

        try:
            async with self.aiohttp_session.post(
                self.translate_url,
                params=translate_params,
                json=translate_payload,
                headers=translate_headers,
                timeout=self.timeout
            ) as response:
                if response.status != 200:
                    logger.error(f"翻译失败，状态码 {response.status}: {await response.text()}")
                    return None
                translation = await response.json()
                return translation[0]["translations"][0]["text"]
        except aiohttp.ClientError as e:
            logger.error(f"翻译请求失败: {e}")
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"解析翻译响应时出错: {e}")
        return None

    async def close(self):
        """关闭持久的aiohttp会话"""
        if self.aiohttp_session:
            await self.aiohttp_session.close()
            logger.info("aiohttp会话已关闭。")

async def main():
    translator = MicrosoftTranslator()
    result = await translator.translate_async("Hello, \n world!\n 1", "auto", "zh")
    if result:
        print(f"翻译文本: {result}")
    else:
        print("翻译失败。")
    # 关闭aiohttp会话
    await translator.close()

if __name__ == "__main__":
    asyncio.run(main())