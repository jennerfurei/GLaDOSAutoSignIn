#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GLaDOS 自动签到（浏览器版，应对 Cloudflare Turnstile）

背景：2026-11-17 起 GLaDOS 签到接口强制 Cloudflare Turnstile 人机验证，
纯 API 请求（无浏览器 token）一律被拒（code:5 reason:turnstile）。
方案：无头 Chromium 加载真实签到页 + Cookie 注入，模拟点击签到按钮
（button.ckb），拦截 /api/user/checkin 响应拿到权威结果。
余额检查与兑换（/api/user/exchange、/api/user/status）走纯 API（实测无需 token）。

要点：
- 点击用 no_wait_after=True（按钮触发 JS 流程而非导航，默认等待会卡死）
- systemd 配了 cgroup 内存隔离（MemoryMax=380M），浏览器失控也不会拖垮整机
- 资源拦截：屏蔽图片/字体/媒体，省内存
- 失败推飞书；兑换成功推飞书并附剩余天数

退出码：0 = 签到成功/已签；1 = 失败
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE = "https://glados.cloud"
CHECKIN_PAGE = BASE + "/console/checkin"
CHECKIN_API = BASE + "/api/user/checkin"
EXCHANGE_API = BASE + "/api/user/exchange"
STATUS_API = BASE + "/api/user/status"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

MAX_RETRY = 3
TURNSTILE_WAIT = 60
EXCHANGE_THRESHOLD = 500
EXCHANGE_PLAN = "plan500"  # 500 积分 -> 100 天


def log(msg: str) -> None:
    print(time.strftime("[%Y-%m-%d %H:%M:%S]"), msg, flush=True)


def notify_feishu(text: str) -> None:
    webhook = os.environ.get("FEISHU_WEBHOOK", "").strip()
    if not webhook:
        log("未配置 FEISHU_WEBHOOK，跳过飞书通知")
        return
    try:
        payload = json.dumps({"msg_type": "text", "content": {"text": text}}).encode()
        req = urllib.request.Request(webhook, data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        log("飞书通知已发送")
    except Exception as e:
        log(f"飞书通知发送失败: {e}")


def api_json(url: str, cookie: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if body is not None else "GET")
    req.add_header("Cookie", cookie)
    if body is not None:
        req.add_header("Content-Type", "application/json;charset=UTF-8")
    req.add_header("User-Agent", UA)
    req.add_header("Referer", CHECKIN_PAGE)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_cookies(raw: str):
    cookies = []
    for pair in raw.split(";"):
        pair = pair.strip()
        if "=" in pair:
            name, _, value = pair.partition("=")
            cookies.append({"name": name.strip(), "value": value.strip(),
                            "domain": "glados.cloud", "path": "/"})
    return cookies


def classify_checkin(data: dict):
    code = int(data.get("code", -1))
    msg = str(data.get("message", ""))
    if code == 5 and data.get("reason") == "turnstile":
        return False, "Turnstile 未通过"
    low = msg.lower()
    if "successful" in low or "got" in low:
        return True, f"签到成功：{msg}"
    if "observation" in low or "tomorrow" in low or "already" in low:
        return True, f"今日已签到：{msg}"
    return False, f"返回异常：code={code} {msg}"


def try_click_turnstile(page) -> None:
    for frame in page.frames:
        if "challenges.cloudflare.com" in (frame.url or ""):
            try:
                cb = frame.locator("input[type='checkbox']")
                if cb.count() > 0 and cb.first.is_visible():
                    cb.first.click(timeout=2000)
                    log("已点击 Turnstile 勾选框")
                    return
                for sel in ["label.ctp-checkbox-label", "body"]:
                    loc = frame.locator(sel)
                    if loc.count() > 0 and loc.first.is_visible():
                        loc.first.click(timeout=2000)
                        log(f"已点击 Turnstile 元素({sel})")
                        return
            except Exception:
                pass


def balance_from_response(data: dict) -> int:
    lst = data.get("list") or []
    if lst and lst[0].get("balance") is not None:
        return round(float(lst[0]["balance"]))
    return int(data.get("points") or 0)


def main() -> int:
    cookie_raw = os.environ.get("GLADOS_COOKIE", "").strip()
    if "koa:sess" not in cookie_raw:
        log("错误：GLADOS_COOKIE 未配置")
        notify_feishu("GLaDOS 签到失败：服务器上未配置 Cookie")
        return 1

    ok = False
    final_msg = ""
    checkin_data = None
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
                  "--disable-extensions", "--disable-background-networking",
                  "--disable-component-update", "--no-first-run",
                  "--js-flags=--max-old-space-size=96"],
        )
        ctx = browser.new_context(user_agent=UA, locale="zh-CN",
                                  viewport={"width": 800, "height": 600})
        ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")

        def _route(route):
            url = route.request.url
            # 白名单：只放行 GLaDOS 与 Cloudflare 人机验证资源，其余全部掐断
            if url.startswith(("https://glados.cloud", "https://challenges.cloudflare.com")) \
                    and route.request.resource_type not in ("image", "font", "media"):
                route.continue_()
            else:
                route.abort()

        ctx.route("**/*", _route)
        ctx.add_cookies(parse_cookies(cookie_raw))

        captured = {}

        def on_response(resp):
            try:
                if resp.request.method == "POST" and \
                        resp.url.rstrip("/").endswith("/api/user/checkin"):
                    captured["checkin"] = resp.json()
                    log(f"拦截到签到响应: {json.dumps(captured['checkin'], ensure_ascii=False)[:200]}")
            except Exception:
                pass

        for attempt in range(1, MAX_RETRY + 1):
            captured.clear()
            # 每次尝试新建页面并在结束后关闭，强制释放上一轮的 JS 堆内存
            page = ctx.new_page()
            page.on("response", on_response)
            try:
                page.goto(CHECKIN_PAGE, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(5000)

                try:
                    page.wait_for_selector("button.ckb", state="visible", timeout=30000)
                except PWTimeout:
                    ok, final_msg = False, "30s 内签到按钮未出现（Cookie 可能失效或页面改版）"
                    break
                if page.locator("button.ckb.is-done").count() > 0:
                    ok, final_msg = True, "今日已签到（页面按钮 is-done）"
                    break
                # 关键：用 JS 派发点击（等同油猴 el.click()），
                # 绕开 Playwright 的可点击性检查——内存紧张时它会拖到超时
                clicked = page.evaluate(
                    """() => {
                        const b = document.querySelector('button.ckb:not(.is-done)');
                        if (!b) return false;
                        b.click();
                        return true;
                    }""")
                if not clicked:
                    ok, final_msg = False, "JS 点击未找到签到按钮"
                    break
                log("已通过 JS 点击签到按钮(button.ckb)")

                deadline = time.time() + TURNSTILE_WAIT
                last_click = 0.0
                while time.time() < deadline:
                    if captured.get("checkin") is not None:
                        ok, final_msg = classify_checkin(captured["checkin"])
                        break
                    if time.time() - last_click > 2.5:
                        try_click_turnstile(page)
                        last_click = time.time()
                    page.wait_for_timeout(1000)
                else:
                    ok, final_msg = False, f"{TURNSTILE_WAIT}s 内未收到签到接口响应"
            except PWTimeout as e:
                ok, final_msg = False, f"页面操作超时: {str(e).splitlines()[0]}"
            except Exception as e:
                ok, final_msg = False, f"页面流程异常: {type(e).__name__}: {e}"

            log(f"第 {attempt} 次尝试: {final_msg}")
            try:
                page.close()  # 立即释放本轮页面内存
            except Exception:
                pass
            if ok:
                break

        browser.close()

    if not ok:
        log(f"签到失败 ❌：{final_msg}")
        notify_feishu(f"GLaDOS 自动签到失败：{final_msg}\n（无头浏览器方案，请手动补签 glados.cloud/console/checkin）")
        return 1

    # ---------- 余额 + 兑换（纯 API，实测无需 Turnstile） ----------
    checkin_data = captured.get("checkin") or {}
    balance = balance_from_response(checkin_data)
    log(f"当前积分余额: {balance}")

    if balance >= EXCHANGE_THRESHOLD:
        log(f"积分 {balance} >= {EXCHANGE_THRESHOLD}，尝试兑换 {EXCHANGE_PLAN}")
        try:
            ex = api_json(EXCHANGE_API, cookie_raw, body={"planType": EXCHANGE_PLAN})
            if int(ex.get("code", -1)) == 0:
                days = str(api_json(STATUS_API, cookie_raw).get("data", {}).get("leftDays", "?"))
                days = f"{float(days):.0f}" if days != "?" else days
                log(f"兑换成功 ✅ 当前剩余 {days} 天")
                notify_feishu(f"GLaDOS 兑换成功 ✅\n{EXCHANGE_THRESHOLD} 积分已兑换 100 天\n当前剩余天数：{days}")
            else:
                log(f"兑换被服务端拒绝: {ex.get('message', ex)}")
                notify_feishu(f"GLaDOS 兑换失败（积分 {balance}）：{ex.get('message', ex)}")
        except Exception as e:
            log(f"兑换请求异常: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
