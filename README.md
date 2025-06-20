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

