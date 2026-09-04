# Cursor Rules for AutoSignIn

## 项目背景
- 维护 `ScriptFile.js` 中的油猴自动签到脚本，以及 `README.md` 中的 Automator 启动指引。
- 目标是保证 Mac 启动后自动打开浏览器并触发 GLaDOS 签到，兼容 Safari 与 Chrome。

## 代码约定
- 语言：纯 JavaScript（Tampermonkey 用户脚本）；保持 IIFE 结构与 `'use strict'`。
- 命名：函数与变量使用动词+名词组合，示例 `simulateClick`、`forceCheckIn`。
- 逻辑：保持单一职责；公共逻辑（按钮搜索、点击模拟）抽离为函数重复使用。
- 注释：只在复杂流程（如 MutationObserver 或调试输出来说明用途）添加简洁中文注释。
- 字符串：以双引号为主，控制台输出包含 Emojis 可保留，用于调试反馈。

## 功能要求
- 签到按钮匹配需兼容“签到”“checkin”“sign in”等关键词，并避开隐藏/禁用按钮。
- 在遮罩（`.ant-spin-spinning`）消失后执行点击；必要时调用 `window.stop()` 加速加载结束。
- 保持 MutationObserver 监听 DOM 变化；提供初始 fallback 检查，避免按钮已存在却未触发。
- 检测不到按钮时需输出调试信息（按钮列表、状态），以便远程排查。
- 若新增逻辑，优先考虑可测试性与可扩展性，例如封装按钮过滤器或可配置的等待超时。

## README 文档
- 保持分步结构（GreasyFork 安装 → 登录 → Automator 创建 → Shell 脚本 → 登录项设置）。
- Safari 与 Chrome 的 `open -a` 命令都要列出；若支持其他浏览器需追加说明。
- 更新脚本行为或依赖时同步 README，特别是自动化步骤与注意事项。

## 质量保障
- 修改脚本后在浏览器控制台模拟按钮状态进行自测。
- 检查 `waitForButtonToAppear` 等引用函数是否实际实现，避免未定义调用。
- 保持输出的 console 日志用于调试，但上线前确认不会阻塞流程。

## 提交与协同
- 每次提交聚焦单一主题（脚本逻辑、文档等），使用中文/英文皆可但需清晰描述。
- 若发现用户手动修改的内容，除非获得授权不得回滚。
- 在 Cursor 中执行重要操作前复读需求，确保与用户目标一致。

## 测试
- 在浏览器中模拟用户行为，验证脚本是否正常工作。
- 若新增逻辑，请在浏览器中模拟用户行为，验证脚本是否正常工作。
