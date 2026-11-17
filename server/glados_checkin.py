#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GLaDOS 自动签到 + 积分满 500 自动兑换 100 天（纯标准库，无第三方依赖）

Cookie 从环境变量 GLADOS_COOKIE 读取（由 systemd EnvironmentFile 注入），
格式：koa:sess=xxx; koa:sess.sig=yyy
可选环境变量 FEISHU_WEBHOOK：签到失败 / 兑换成功 / 兑换异常时推送飞书群通知。

逻辑：
1. POST /api/user/checkin 签到（重试 ×3）
2. 从签到返回的流水里取当前积分余额（与页面 UI 同源：list[0].balance）
3. 余额 >= 500 时 POST /api/user/exchange {planType:"plan500"} 兑换 100 天
   - 余额不足：不做任何处理
   - 兑换成功：飞书推送「兑换成功 + 当前剩余天数」
4. 退出码：0 = 正常；1 = 失败（飞书告警人工介入）
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "https://glados.cloud"
CHECKIN_URL = BASE + "/api/user/checkin"
EXCHANGE_URL = BASE + "/api/user/exchange"
STATUS_URL = BASE + "/api/user/status"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

EXCHANGE_THRESHOLD = 500   # 积分门槛
EXCHANGE_PLAN = "plan500"  # 500 积分 -> 100 天（与前端档位一致）

RETRY_COUNT = 3
RETRY_INTERVAL = 10  # 秒


def log(msg: str) -> None:
    # systemd 会把 stdout/stderr 收进 journald，带时间戳输出即可
    print(time.strftime("[%Y-%m-%d %H:%M:%S]"), msg, flush=True)


def notify_feishu(text: str) -> None:
    webhook = os.environ.get("FEISHU_WEBHOOK", "").strip()
    if not webhook:
        log("未配置 FEISHU_WEBHOOK，跳过飞书通知")
        return
    try:
        payload = json.dumps({"msg_type": "text", "content": {"text": text}}).encode()
        req = urllib.request.Request(
            webhook, data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        log("飞书通知已发送")
    except Exception as e:  # 通知失败不影响主流程
        log(f"飞书通知发送失败: {e}")


def http_json(url, cookie, body=None, method="GET"):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Cookie", cookie)
    if body is not None:
        req.add_header("Content-Type", "application/json;charset=UTF-8")
    req.add_header("User-Agent", UA)
    req.add_header("Referer", BASE + "/console/checkin")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_left_days(cookie: str) -> str:
    try:
        data = http_json(STATUS_URL, cookie)
        days = str(data.get("data", {}).get("leftDays", ""))
        return f"{float(days):.0f}" if days else "未知"
    except Exception as e:
        log(f"获取剩余天数失败: {e}")
        return "未知"


def balance_from_checkin(data: dict) -> int:
    """与页面 UI 同源取余额：优先流水最新一条的 balance，兜底 points 字段"""
    lst = data.get("list") or []
    if lst and lst[0].get("balance") is not None:
        return round(float(lst[0]["balance"]))
    return int(data.get("points") or 0)


def main() -> int:
    cookie = os.environ.get("GLADOS_COOKIE", "").strip()
    if not cookie or "koa:sess" not in cookie:
        log("错误：GLADOS_COOKIE 未配置或缺少 koa:sess 字段")
        notify_feishu("GLaDOS 签到失败：服务器上未配置 Cookie")
        return 1

    # ---------- 1. 签到 ----------
    last_msg = ""
    checkin_data = None
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            checkin_data = http_json(CHECKIN_URL, cookie, body={"portal": "office"}, method="POST")
            last_msg = str(checkin_data.get("message", ""))
            log(f"接口返回: {last_msg}")
            msg_lower = last_msg.lower()
            if "successful" in msg_lower or "got" in msg_lower:
                log("签到成功 ✅")
                break
            if "tomorrow" in msg_lower or "already" in msg_lower or "observation" in msg_lower:
                log("今日已签到，跳过 ✅")
                break
            log(f"第 {attempt} 次返回语义异常，视为失败")
        except urllib.error.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode("utf-8", errors="replace")[:200]
            except Exception:
                pass
            log(f"第 {attempt} 次 HTTP {e.code}: {body_text}")
            if e.code in (401, 403):
                last_msg = f"HTTP {e.code}（大概率 Cookie 过期）"
                break
        except Exception as e:
            log(f"第 {attempt} 次请求异常: {e}")
            last_msg = str(e)
        checkin_data = None
        if attempt < RETRY_COUNT:
            time.sleep(RETRY_INTERVAL)

    if checkin_data is None:
        log(f"签到失败 ❌：{last_msg}")
        notify_feishu(f"GLaDOS 自动签到失败：{last_msg}\n请检查 Cookie 是否过期并更新服务器 /opt/glados-checkin/cookie.env")
        return 1

    # ---------- 2. 积分余额 ----------
    balance = balance_from_checkin(checkin_data)
    log(f"当前积分余额: {balance}")

    # ---------- 3. 满 500 自动兑换 100 天 ----------
    if balance < EXCHANGE_THRESHOLD:
        log(f"积分 {balance} 未达 {EXCHANGE_THRESHOLD}，不兑换")
        return 0

    log(f"积分 {balance} >= {EXCHANGE_THRESHOLD}，尝试兑换 {EXCHANGE_PLAN}")
    try:
        ex = http_json(EXCHANGE_URL, cookie, body={"planType": EXCHANGE_PLAN}, method="POST")
        if int(ex.get("code", -1)) == 0:
            days = get_left_days(cookie)
            log(f"兑换成功 ✅，当前剩余 {days} 天")
            notify_feishu(f"GLaDOS 兑换成功 ✅\n{EXCHANGE_THRESHOLD} 积分已兑换 100 天\n当前剩余天数：{days}")
        else:
            log(f"兑换被服务端拒绝: {ex.get('message', ex)}")
            notify_feishu(f"GLaDOS 兑换失败（积分 {balance}）：{ex.get('message', ex)}")
            return 1
    except Exception as e:
        log(f"兑换请求异常: {e}")
        notify_feishu(f"GLaDOS 兑换请求异常（积分 {balance}）：{e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
