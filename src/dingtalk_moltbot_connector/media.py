"""钉钉图片上传辅助模块

通过 system prompt 引导 Moltbot 将图片上传到钉钉，
使 AI Card 中的图片能够正确显示。
"""

import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger("dingtalk_moltbot_connector")

# access_token 缓存：(token, 过期时间戳)
_token_cache: dict[str, tuple[str, float]] = {}


def get_dingtalk_access_token(client_id: str, client_secret: str) -> Optional[str]:
    """获取钉钉 access_token（带缓存，有效期内不重复请求）

    Args:
        client_id: 钉钉 AppKey
        client_secret: 钉钉 AppSecret

    Returns:
        access_token 字符串，失败返回 None
    """
    cache_key = client_id
    cached = _token_cache.get(cache_key)
    if cached:
        token, expires_at = cached
        if time.time() < expires_at:
            return token

    try:
        resp = httpx.get(
            "https://oapi.dingtalk.com/gettoken",
            params={"appkey": client_id, "appsecret": client_secret},
            timeout=10,
        )
        data = resp.json()
        if data.get("errcode") == 0:
            token = data.get("access_token", "")
            # 钉钉 token 有效期 7200 秒，提前 5 分钟刷新
            expires_in = data.get("expires_in", 7200)
            _token_cache[cache_key] = (token, time.time() + expires_in - 300)
            return token
        logger.warning(f"获取 access_token 失败: {data}")
        return None
    except Exception as e:
        logger.warning(f"获取 access_token 异常: {e}")
        return None


def build_media_system_prompt(client_id: str, client_secret: str) -> str:
    """生成引导 Moltbot 上传图片到钉钉的 system prompt

    Args:
        client_id: 钉钉 AppKey
        client_secret: 钉钉 AppSecret

    Returns:
        system prompt 字符串，获取 token 失败时返回空字符串
    """
    access_token = get_dingtalk_access_token(client_id, client_secret)
    if not access_token:
        return ""

    return f"""## 钉钉图片显示规则（强制）

你正在钉钉中与用户对话。钉钉**只能显示已上传的图片**，无法显示本地路径。

### 禁止使用

- `file://` 路径
- `attachment://` 路径
- `/tmp/xxx.jpg` 等本地路径
- `https://static.dingtalk.com/media/xxx` 等猜测的 URL
- 任何未经上传的图片链接

### 正确方式

**任何时候**需要向用户展示图片，都必须：

1. **先上传**：执行 curl 命令上传到钉钉
2. **确认成功**：检查返回的 media_id
3. **再回复**：用 media_id 构造 markdown 图片

### 上传命令

```bash
curl -s -X POST "https://oapi.dingtalk.com/media/upload?access_token={access_token}&type=image" -F "media=@/实际图片路径.jpg"
```

### 返回格式

```json
{{"errcode":0,"errmsg":"ok","media_id":"@lADPxxxxxx"}}
```

### 回复格式

```markdown
![描述](@lADPxxxxxx)
```

**注意**：media_id 以 `@` 开头，直接使用，不拼接任何 URL 前缀。

### 工作流程示例

用户说"拍张照"：
1. 执行拍照，得到 `/tmp/camera-snap-xxx.jpg`
2. 执行: `curl -s -X POST "https://oapi.dingtalk.com/media/upload?access_token={access_token}&type=image" -F "media=@/tmp/camera-snap-xxx.jpg"`
3. 从返回中提取 `media_id`（如 `@lADPxxxxxx`）
4. 回复: `这是拍摄的照片：![照片](@lADPxxxxxx)`

**关键**：必须等 curl 执行成功并拿到 media_id 后，才能回复包含图片的消息！
"""
