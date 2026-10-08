# 📌 GLaDOS 自动签到

一个基于 **GitHub Actions** 的 **GLaDOS 自动签到脚本**。

**无需服务器、无需编程基础**，每天自动帮你签到。

本项目 Fork 自 [MZRidaz/GLaDOS-Auto-Checkin](https://github.com/MZRidaz/GLaDOS-Auto-Checkin)，
已合并上游 `b51eb40`，并保留本分支的多域名切换、原有 Telegram 配置、奖励展示和独立保活策略。

---

## ✨ 功能特性

- ✅ 每天自动签到，已签到自动识别
- 👥 支持多账号（`|||`、`&` 或换行连接）
- 📊 查询总积分和剩余天数
- 📬 8 种推送渠道：PushDeer / Server酱 / Telegram / PushPlus / 钉钉 / 飞书 / 企业微信 / 云湖
- 🔄 网络请求自动重试（指数退避）
- 🔒 日志脱敏（邮箱/Cookie 自动隐藏）
- ✅ Cookie 结构预验证（前缀无关，自动兼容 `koa:` / `gld:` 等任意前缀）
- 🔧 每天独立检查仓库活动，45 天无提交时自动空提交保活
- 支持 `glados.cloud` / `glados.one` / `glados.network` 自动切换；Actions Variables 的 `GLADOS_SITE` 可指定优先域名
- 保留积分明细、奖励展示，任意账号失败时 Actions 标红
- 💎 积分自动兑换（可选，消耗积分兑换会员天数）
- 🆓 完全免费

---

## 📂 项目结构

```
.
├── checkin.py                 # 签到脚本
├── test_checkin.py            # 模拟接口回归测试
└── .github/workflows/
    └── glados.yml             # GitHub Actions 配置
```

---

## 🚀 使用教程

### 第一步：Fork 本项目

点击右上角 **Fork**，Fork 到你自己的 GitHub 账号下。

---

### 第二步：获取 GLaDOS Cookie

1. 打开浏览器，登录 https://glados.cloud
2. 按 **F12** 打开开发者工具
3. 在 `Network` 面板刷新页面，找到 `/api/user/status` 请求
4. 复制 `Request Headers` 中完整的 `Cookie` 值

示例（以浏览器实际签发的名称和值为准）：

```
gld:sess=xxxxxx; gld:sess.sig=yyyyyy
```

旧版签发的 `koa:sess=xxxxxx; koa:sess.sig=yyyyyy` 同样支持，**必须保留浏览器实际签发的前缀，无需手动转换**。

⚠️ **必须是完整的一整段**，且 `sess` 与 `sess.sig` 两个字段**必须同时存在、前缀一致**。
只复制其中一个会导致签到失败（脚本会明确指出缺少哪个字段）。

> 💡 脚本采用**结构校验**：只校验「`<前缀>:sess` 与同前缀 `:sess.sig` 成对」，
> 不写死具体前缀。因此 GLaDOS 即便再次变更前缀名，脚本也能自动识别，无需修改代码。
> **不要把 `gld:` 改成 `koa:`** —— 改前缀会让服务端无法识别 session，导致「没有权限」。

---

### 第三步：添加 GitHub Secrets

进入你 Fork 后的仓库：

1. **Settings** → **Secrets and variables** → **Actions** → **Secrets** 标签页
2. 点击 **New repository secret**
3. 添加：
   - **Name**：`COOKIES`
   - **Value**：粘贴刚才复制的 Cookie
4. 点击 **Save**

建议将 Cookie 放在 Secrets 中；兼容读取 Variables 中的 `COOKIES`，Secrets 优先。变量名必须是 `COOKIES`。

---

### 第四步：（可选）选择优先站点

进入 **Settings → Secrets and variables → Actions → Variables**，添加：

| Name | 示例 Value | 用途 |
|------|------------|------|
| `GLADOS_SITE` | `glados.one` | 优先尝试获取 Cookie 时使用的站点 |

默认顺序为 `glados.cloud` → `glados.one` → `glados.network`。
配置后先尝试指定站点，再尝试其余候选站点；成功、已签到或查到账号邮箱后停止切换。
不同域名的登录状态不一定通用，建议填写获取 Cookie 的域名。

### 第五步：（可选）配置推送

在 GitHub Secrets 中添加对应的环境变量：

| 渠道 | 必填环境变量 | 可选 |
|------|-------------|------|
| PushDeer | `SENDKEY` | - |
| Server酱 | `SERVERCHAN_KEY` | - |
| Telegram | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | 兼容上游 `TG_BOT_TOKEN` + `TG_CHAT_ID`；原配置优先，分段发送完整结果 |
| PushPlus | `PUSHPLUS_TOKEN` | - |
| 钉钉机器人 | `DINGTALK_WEBHOOK` | `DINGTALK_SECRET` |
| 飞书机器人 | `FEISHU_WEBHOOK` | `FEISHU_SECRET` |
| 企业微信机器人 | `WECOM_BOT_WEBHOOK` | - |
| 云湖机器人 | `YUNHU_TOKEN` + `YUNHU_RECV_ID` | `YUNHU_RECV_TYPE` |

Telegram 两套配置各自需要完整的一对 Token 和 Chat ID。两套都完整时，优先使用
`TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`，只发送一次。已有配置无需改名。
不配置推送也可正常签到；Telegram 分段发送完整汇总，其他渠道最多发送前 3000 个字符。

> 🔑 **钉钉 / 飞书加签说明**：若机器人启用了「加签」校验，则 `DINGTALK_WEBHOOK` + `DINGTALK_SECRET`（或 `FEISHU_WEBHOOK` + `FEISHU_SECRET`）**必须同时配置**。只配 webhook 不配 secret 时，脚本会发送无签名请求并给出告警，加签机器人将鉴权失败。

---

### 第六步：（可选）积分自动兑换

在 GitHub Secrets 中添加 `EXCHANGE_PLAN`（或 `GLADOS_EXCHANGE_PLAN`，二选一）即可启用自动兑换积分功能。**不配置则默认不兑换**，不影响任何现有签到逻辑。

| 配置值 | 消耗积分 | 兑换天数 |
|--------|---------|---------|
| `plan100` | 100 积分 | 10 天 |
| `plan200` | 200 积分 | 30 天 |
| `plan500` | 500 积分 | 100 天 |

机制说明：

- 在签到成功、已签到或查到账号邮箱的站点，成功查询到积分且**总积分 ≥ 计划所需积分**时执行兑换。
- 每个账号每次运行最多发起一次兑换请求，兑换请求不自动重试。配置后会在后续运行中继续按条件兑换，直到移除配置。
- 同时设置两个计划变量时，非空的 `EXCHANGE_PLAN` 优先；无效计划会记录警告并跳过兑换。
- 兑换结果会附加到签到日志行末尾，例如：`| 兑换:🎁 兑换成功(+30天)`。
- 兑换失败 / 异常**不影响**签到结果与运行退出码。

---

## 👥 多账号配置

多个账号的 Cookie 用 `|||`、`&` 或**换行**连接（三种分隔符均可混用，推荐使用 `|||` 以避免与 Cookie 值冲突）：

```
cookie_账号1 ||| cookie_账号2 ||| cookie_账号3
```

或

```
cookie_账号1
cookie_账号2
cookie_账号3
```

⚠️ Cookie 值本身不得包含 `|||`、`&` 或换行符，否则会被错误拆分。推荐使用 `|||` 作为分隔符，因为 Cookie 值中几乎不可能出现该字符串。

---

## ⏰ 签到时间

每天 **UTC 04:00**（北京时间 **中午 12 点**）自动运行。GitHub 定时任务可能延迟。

首次配置或更新 Cookie 后，进入 **Actions → GLaDOS Auto Checkin → Run workflow**
手动运行一次。签到任务超时限制为 15 分钟，保活任务为 5 分钟。

---

## 📋 签到结果

| 状态 | 说明 |
|------|------|
| ✅ 成功 | 签到成功，显示获得积分 |
| 🔄 已签到 | 今日已签到过 |
| ❌ 失败 | 签到失败，显示原因 |

汇总包含脱敏邮箱、签到状态、实际站点、总积分、奖励和剩余天数；无法取得的字段显示 `-`。

- 所有账号成功或已签到：退出码 `0`。
- 任意账号失败、Cookie 格式不合法或未配置 `COOKIES`：退出码 `1`，签到任务标红。
- 通知发送失败不改变签到退出码；**Telegram 推送成功只表示通知送达**。
- `keepalive` 与 `checkin` 是独立任务，查看签到结果时请打开 `checkin` 日志。

---

## ❓ 常见问题

**Q: 签到提示「没有权限」/ 鉴权失败？**

A: 表示请求未通过站点权限校验，常见原因是 Cookie 失效、不完整或登录域名不匹配。
请重新登录，确认浏览器 `/api/user/status` 能返回账号信息，复制完整请求 Cookie 更新
Secrets 中的 `COOKIES`，并将 `GLADOS_SITE` 设为相同域名。不要公开 Cookie。
若日志提示「会话字段不成对」或输出了「实际键名」，则多为复制遗漏了 `sess` / `sess.sig` 其中之一，重新完整复制即可。

> 💡 脚本会自动识别 `koa:` / `gld:` 等任意前缀，**无需手动修改前缀**；反之，手动把前缀改错（如把 `gld:` 改成 `koa:`）会让服务端无法识别 session。

**Q: Cookie 有有效期吗？**

A: 有。Cookie 会随会话过期，需重新登录获取最新 Cookie 并更新 Secrets。

**Q: Actions 被暂停了？**

A: 项目每天检查仓库活动，45 天无提交时自动保活。已停用的工作流需先在 Actions 点击 `Enable workflow`，再手动运行。

**Q: 日志中的邮箱为什么显示不完整？**

A: 出于隐私保护，邮箱会自动脱敏（如 `te***t@example.com`）。

**Q: 可以同时配置多个推送渠道吗？**

A: 可以，配置多个 Secrets 即可同时推送。

---

## 防止工作流因长期无活动而停用

GitHub 会停用公开仓库中连续 60 天没有仓库活动的定时工作流。
工作流每天会独立检查默认分支的最新提交时间；如果已满 45 天没有提交，
就使用内置的 `GITHUB_TOKEN` 创建并推送一次空提交，刷新仓库活动时间。
空提交不会修改项目文件，也不需要额外配置 PAT；签到任务失败不会阻止保活任务。

保活任务声明了 `contents: write` 权限。如果仓库或组织策略限制写入，
或者默认分支的保护规则禁止机器人直接推送，需要调整相应策略才能使保活生效。

如果工作流已经被禁用，请先将此更新同步到默认分支，再进入仓库的 `Actions`，
选择 `GLaDOS Auto Checkin` 并点击 `Enable workflow`，随后使用 `Run workflow`
手动运行一次，确认 `keepalive` 任务成功。已停用的工作流无法自行运行来恢复。


## 本地验证

使用 Python 3.11，在安装依赖后运行模拟接口测试：

```bash
python -m pip install "requests==2.32.3"
python -m unittest -v test_checkin.py
```

测试不需要真实 Cookie，不会发送真实签到、兑换或推送请求。

## 上游同步说明

本分支已合并上游 `b51eb40`：Cookie 归一化与结构校验、网络重试、八种推送渠道、
积分查询和可选兑换，以及 Python 3.11 工作流配置。

合并时保留了本分支的以下行为：

- 多域名切换及 `GLADOS_SITE` 优先站点。
- 原有 `TELEGRAM_*` Secrets，兼容上游 `TG_*`，长消息分段发送。
- 签到积分明细和奖励解析，兼容 `code=1` 携带积分明细的成功响应。
- 任意账号失败时返回非零退出码。
- 每天检查、45 天无提交后执行空提交的独立保活任务。

上游历史版本说明见[源仓库](https://github.com/MZRidaz/GLaDOS-Auto-Checkin)。
