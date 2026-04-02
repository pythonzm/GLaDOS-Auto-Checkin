# GLaDOS 自动签到

这是一个基于 **GitHub Actions** 的 **GLaDOS 自动签到脚本**。
无需服务器，也不需要额外常驻环境，仓库工作流会按计划自动执行签到。

---

## 功能说明

- 每天自动签到
- 自动识别重复签到，避免误判
- 支持多账号
- 支持 `glados.one` / `glados.network` / `glados.cloud`
- 可选推送签到结果到 Telegram Bot
- 依赖 GitHub Actions，可直接 Fork 使用

---

## 项目结构

```text
.
├── checkin.py                 # 签到脚本
└── .github/workflows/
    └── glados.yml             # GitHub Actions 配置
```

---

## 使用教程

### 第一步：Fork 仓库

1. 点击仓库右上角的 `Fork`
2. 将仓库 Fork 到你自己的 GitHub 账号

后续所有配置都在你自己的仓库里完成。

---

### 第二步：获取 GLaDOS Cookie

1. 打开 `https://glados.one`、`https://glados.network` 或 `https://glados.cloud` 中任意一个并登录
2. 按 `F12` 打开开发者工具
3. 在浏览器存储中找到当前登录站点对应的 Cookie
4. 复制完整 Cookie 内容

示例：

```text
koa:sess=xxxxxx; koa:sess.sig=yyyyyy
```

注意必须复制完整 Cookie，不能只复制其中一个字段。

这三个域名本质上是同一个站点，脚本会自动尝试可用域名完成签到。

---

### 第三步：添加 GitHub Secrets

进入你 Fork 后的仓库：

1. 点击 `Settings`
2. 进入 `Secrets and variables` -> `Actions`
3. 点击 `New repository secret`

添加必填 Secret：

- `COOKIES`：你的 GLaDOS Cookie

---

### 第四步：配置 Telegram Bot 推送（可选）

如果你希望收到签到通知，需要再配置两个 Secret：

- `TELEGRAM_BOT_TOKEN`：Telegram Bot 的 Token
- `TELEGRAM_CHAT_ID`：接收消息的 Chat ID

创建 Bot 的基本流程：

1. 在 Telegram 中找到 `@BotFather`
2. 发送 `/newbot`，按提示创建机器人
3. 记录返回的 Bot Token
4. 给你的 Bot 发送一条消息
5. 通过 Telegram Bot API 或其他方式获取当前会话的 Chat ID

如果不配置这两个 Secret，脚本仍然可以签到，只是不会发送通知。

---

## 多账号配置

多个账号的 Cookie 使用 `&` 连接，格式如下：

```text
cookie_账号1 & cookie_账号2 & cookie_账号3
```

注意：

- 不要换行
- 不要用逗号分隔
- 每个 Cookie 都必须是完整的一整段

---

## 自动执行时间

工作流默认配置为：

```text
每天 UTC 04:00 自动运行
```

换算为北京时间是每天中午 12:00。

如果你想立即测试，也可以手动触发工作流中的 `workflow_dispatch`。
