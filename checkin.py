import json
import os
import random
import re
import sys
import time
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple

import requests


TIMEOUT = 10
TELEGRAM_MESSAGE_LIMIT = 4096
SUPPORTED_DOMAINS = ("glados.one", "glados.network", "glados.cloud")
CHECKIN_TOKEN = "glados.one"

HEADERS_BASE = {
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "content-type": "application/json;charset=UTF-8",
}


def safe_json(response: requests.Response) -> dict:
    """安全解析 JSON，失败时返回空字典。"""
    try:
        return response.json()
    except Exception:
        return {}


def console_print(message: str) -> None:
    """兼容 Windows 控制台编码的输出。"""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    sys.stdout.buffer.write(f"{message}\n".encode(encoding, errors="replace"))
    sys.stdout.flush()


def normalize_domain(domain: str) -> str:
    """标准化域名输入，兼容带协议头的配置。"""
    normalized = domain.strip().lower()
    if normalized.startswith("https://"):
        normalized = normalized[8:]
    elif normalized.startswith("http://"):
        normalized = normalized[7:]
    return normalized.split("/", 1)[0]


def get_candidate_domains() -> List[str]:
    """返回按优先级排序的候选站点列表。"""
    preferred = normalize_domain(os.getenv("GLADOS_SITE", ""))
    candidates: List[str] = []

    if preferred:
        candidates.append(preferred)

    for domain in SUPPORTED_DOMAINS:
        if domain not in candidates:
            candidates.append(domain)

    return candidates


def build_site_request(domain: str, cookie: str) -> dict:
    """构造指定站点的请求信息。"""
    base_url = f"https://{domain}"
    headers = dict(HEADERS_BASE)
    headers["origin"] = base_url
    headers["referer"] = f"{base_url}/console/checkin"
    headers["cookie"] = cookie
    return {
        "domain": domain,
        "checkin_url": f"{base_url}/api/user/checkin",
        "status_url": f"{base_url}/api/user/status",
        "payload": {"token": CHECKIN_TOKEN},
        "headers": headers,
    }


def try_checkin(session: requests.Session, cookie: str, domains: List[str]) -> dict:
    """按域名顺序尝试签到，命中后立即返回。"""
    last_result = {}

    for domain in domains:
        request_data = build_site_request(domain, cookie)
        try:
            response = session.post(
                request_data["checkin_url"],
                headers=request_data["headers"],
                data=json.dumps(request_data["payload"]),
                timeout=TIMEOUT,
            )
        except Exception:
            continue

        response_data = safe_json(response)
        message = response_data.get("message", "")
        if not message:
            continue
        if "token error" in message.lower():
            continue

        status, is_success, is_fail, is_repeat = get_status_text(message, response_data)
        status_data = {}
        try:
            status_response = session.get(
                request_data["status_url"],
                headers=request_data["headers"],
                timeout=TIMEOUT,
            )
            status_data = safe_json(status_response).get("data") or {}
        except Exception:
            status_data = {}

        result = {
            "domain": domain,
            "checkin_data": response_data,
            "status_data": status_data,
            "status": status,
            "is_success": is_success,
            "is_fail": is_fail,
            "is_repeat": is_repeat,
        }
        if status_data.get("email") or status_data.get("leftDays") is not None:
            return result
        if is_success or is_repeat:
            return result
        last_result = result

    return last_result


def split_telegram_message(title: str, content: str) -> List[str]:
    """按 Telegram 单条消息长度限制拆分内容。"""
    prefix = f"{title}\n\n"
    if len(prefix) + len(content) <= TELEGRAM_MESSAGE_LIMIT:
        return [prefix + content]

    chunks: List[str] = []
    current = prefix
    for line in content.splitlines():
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) <= TELEGRAM_MESSAGE_LIMIT:
            current = candidate
            continue

        if current:
            chunks.append(current)
        current = line

    if current:
        chunks.append(current)

    return chunks or [prefix.strip()]


def push_telegram(bot_token: str, chat_id: str, title: str, content: str) -> None:
    """通过 Telegram Bot 推送签到结果。"""
    if not bot_token or not chat_id:
        console_print("未配置 Telegram Bot 推送，请设置 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    try:
        for message in split_telegram_message(title, content):
            response = requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "disable_web_page_preview": True,
                },
                timeout=TIMEOUT,
            )
            result = safe_json(response)
            if response.status_code == 200 and result.get("ok") is True:
                continue

            description = result.get("description", f"HTTP {response.status_code}")
            console_print(f"Telegram 推送失败: {description}")
            return

        console_print("Telegram 推送成功")
    except Exception as exc:
        console_print(f"Telegram 推送异常: {exc}")


def get_status_text(message: str, checkin_data: Optional[dict] = None) -> Tuple[str, bool, bool, bool]:
    """根据签到接口返回文案判断签到结果。"""
    message_lower = message.lower()
    checkin_data = checkin_data or {}
    if checkin_data.get("code") == 1 and checkin_data.get("list"):
        return "✅ 成功", True, False, False
    if "checkin!" in message_lower and "get" in message_lower:
        return "✅ 成功", True, False, False
    if "observation logged" in message_lower or "return tomorrow" in message_lower:
        return "✅ 成功", True, False, False
    if "got" in message_lower:
        return "✅ 成功", True, False, False
    if "repeat" in message_lower or "already" in message_lower:
        return "🔁 已签到", False, False, True
    return "❌ 失败", False, True, False


def format_decimal(value) -> str:
    """格式化小数，去掉无意义的尾随 0。"""
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)
    normalized = format(number.normalize(), "f")
    return normalized.rstrip("0").rstrip(".") if "." in normalized else normalized


def extract_points(checkin_data: dict) -> str:
    """提取当前积分，优先使用签到明细中的余额。"""
    entries = checkin_data.get("list") or []
    for entry in entries:
        if entry.get("asset") == "points" and entry.get("balance") is not None:
            return format_decimal(entry.get("balance"))

    points = checkin_data.get("points")
    if points is not None:
        return format_decimal(points)

    return "-"


def extract_reward(checkin_data: dict) -> str:
    """提取奖励信息，优先使用积分变化，其次从消息里提取奖励天数。"""
    entries = checkin_data.get("list") or []
    for entry in entries:
        if entry.get("asset") == "points" and entry.get("change") is not None:
            return f"{format_decimal(entry.get('change'))} 积分"

    message = str(checkin_data.get("message", ""))
    matched = re.search(r"get\s+(\d+)\s+day", message, re.IGNORECASE)
    if matched:
        return f"{matched.group(1)} 天"

    return "-"


def build_account_summary(
    index: int,
    email: str,
    domain: str,
    status: str,
    points: str,
    reward: str,
    days: str,
    message: str = "",
) -> str:
    """格式化单个账号的汇总信息。"""
    summary = (
        f"{index}. {email} | {status} | 站点:{domain} | "
        f"积分:{points} | 奖励:{reward} | 剩余天数:{days}"
    )
    if message and status.startswith("❌"):
        return f"{summary} | 消息:{message}"
    return summary


def main() -> None:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    cookies_env = os.getenv("COOKIES", "")
    cookies = [cookie.strip() for cookie in cookies_env.split("&") if cookie.strip()]
    domains = get_candidate_domains()

    if not cookies:
        push_telegram(bot_token, chat_id, "GLaDOS 签到", "❌ 未检测到 COOKIES")
        return

    session = requests.Session()
    success_count = 0
    fail_count = 0
    repeat_count = 0
    lines: List[str] = []

    for index, cookie in enumerate(cookies, start=1):
        email = "unknown"
        domain = "-"
        points = "-"
        reward = "-"
        days = "-"

        result = try_checkin(session, cookie, domains)
        if not result:
            fail_count += 1
            lines.append(build_account_summary(index, email, domain, "❌ 异常", points, reward, days))
            time.sleep(random.uniform(1, 2))
            continue

        domain = result["domain"]
        status = result["status"]
        checkin_data = result["checkin_data"]
        message = str(checkin_data.get("message", ""))
        status_data = result.get("status_data") or {}
        is_success = result["is_success"]
        is_fail = result["is_fail"]
        is_repeat = result["is_repeat"]
        points = extract_points(checkin_data)

        if is_success:
            success_count += 1
            reward = extract_reward(checkin_data)
        if is_fail:
            fail_count += 1
        if is_repeat:
            repeat_count += 1
            reward = extract_reward(checkin_data)

        email = status_data.get("email", email)
        left_days = status_data.get("leftDays")
        if left_days is not None:
            days = str(int(float(left_days)))

        lines.append(build_account_summary(index, email, domain, status, points, reward, days, message))
        time.sleep(random.uniform(1, 2))

    title = f"GLaDOS 签到完成 ✅{success_count} ❌{fail_count} 🔁{repeat_count}"
    content = "\n".join(lines)

    console_print(content)
    push_telegram(bot_token, chat_id, title, content)


if __name__ == "__main__":
    main()
