# Musinsa Price Watcher

这是一个用于监测 무신사 商品价格变化的 Flask Web App，同时已经补好了 iPhone 可安装的 Capacitor 包装方案。

## 功能

- 添加 무신사 商品链接
- 定时检查价格变化
- 价格变化邮件提醒
- 手机端友好的界面
- 支持通过 Capacitor 打包成 iPhone App

## 运行 Web 版

```bash
python app.py
```

然后在浏览器打开：

```text
http://127.0.0.1:5000
```

## Render 部署

Render 会把你的 Flask 服务部署到公网 HTTPS，这样 iPhone App 才能正常访问。

### 需要的文件

- `requirements.txt`
- `app.py`
- `database.py`
- `fetcher.py`
- `notifier.py`
- `config.py`

### 建议的启动命令

```bash
python app.py
```

### 环境变量建议

- `PORT`：Render 会自动提供
- `MAIL_USER`：发件邮箱
- `MAIL_PASSWORD`：邮箱授权码

## iPhone 打包前提

你需要准备：

- Mac
- Xcode
- Apple ID
- Node.js / npm
- 一个可公网访问的 HTTPS 后端地址

## iPhone 安装步骤

1. 先把 Flask 网站部署到 Render
2. 把 Render 给你的公网 HTTPS 地址填到 `capacitor.config.ts` 的 `server.url`
3. 在项目根目录执行：

```bash
npm install
npx cap add ios
npx cap sync ios
npx cap open ios
```

4. 在 Xcode 中选择 Team
5. 连接 iPhone 真机并运行

## 配置说明

`config.py` 里可以设置：

- 邮件 SMTP
- 检查间隔
- 是否使用浏览器抓取

## 重要说明

- 如果 `server.url` 仍然是 `https://YOUR-DOMAIN-HERE`，iPhone App 不能正常访问网页
- 如果你愿意，我可以继续帮你把项目改成“前端静态内置 + API 后端”的结构，这样更适合原生 App 打包
