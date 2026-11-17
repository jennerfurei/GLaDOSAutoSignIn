# GLaDOSAutoSignIn
mac os automatic sign in GLaDos

1.在GreasyFork (油叉)搜索GLaDOS 自动签到（MutationObserver 版），安装插件
2.在浏览器登录GlaDOS
3.Mac os 使用 Automator 创建开机启动应用

	1.	打开 Automator.app
	•	可通过 Spotlight 搜索 “Automator”
	2.	选择“新建文稿” → 选择类型为 “应用程序”
	3.	添加操作：运行 Shell 脚本
	•	搜索 “运行 Shell 脚本”，拖入右侧工作区
	4.	输入脚本内容：
    如果你使用 Safari：open -a "Safari" "https://glados.network/console/checkin"
    如果你使用 Chrome：open -a "Google Chrome" "https://glados.network/console/checkin"
    5.	保存
	•	命名为例如 OpenGLaDOS.app
	•	保存到你喜欢的位置，比如 ~/Applications
	6.	设置开机启动：
	•	系统设置 → 登录项（登录与启动项）→ 打开用户登录项
	•	点击「+」添加刚刚保存的 Automator 应用

4.测试auto g i t

## 2026-11-16 更新：已迁出本机，改为阿里云服务器定时签到（已废止）

服务器方案因 GLaDOS 接入 Cloudflare Turnstile 人机验证而失效，并于 2026-11-17 从服务器全部移除。

## 2026-11-17 更新：恢复本机方案

- 应用：`~/Applications/AutoSignGlaDOS.app`（AppleScript 版，等价于原 Automator 方案，作用是拉起 Chrome 打开 `https://glados.cloud/console/checkin`）
- 登录项：系统设置 → 通用 → 登录项与扩展 → 添加 `~/Applications/AutoSignGlaDOS.app`（或终端跑：
  `osascript -e 'tell application "System Events" to make login item at end with properties {path:"/Users/hanzc/Applications/AutoSignGlaDOS.app", name:"AutoSignGlaDOS", hidden:false}'`）
- 油猴脚本：`ScriptFile.js` 的 `@match` 已修正为 `glados.cloud`（`.network` 保留兜底），需在 Tampermonkey 里更新已安装的那份

### 自动兑换（2026-11-16 加入）

签到后自动检查积分余额（取自签到返回流水 `list[0].balance`，与页面 UI 同源）：
余额 ≥ 500 时调 `POST /api/user/exchange {"planType":"plan500"}` 兑换 100 天，成功后飞书推送「兑换成功 + 当前剩余天数」（天数取 `/api/user/status` 的 `leftDays`）；余额不足不做任何处理。
档位来源为前端硬编码：plan100=100→10天、plan200=200→30天、plan500=500→100天。