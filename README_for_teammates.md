# 무신사 收藏价格监测（给同事的使用说明）

这是一个**本地小网站**，用来监测你在 무신사 收藏的商品价格，价格变动时可以发邮件提醒你。

> 重要：每个人在自己的电脑上跑一份即可，数据互不影响。

---

## 一、准备工作

- 需要有 **Python 3**（Mac 和 Windows 都可以）。
  - 不确定是否安装：打开终端 / 命令提示符，输入 `python --version` 或 `python3 --version` 看一下。
- 解压你收到的 `musinsa-price-watcher.zip`，得到一个文件夹，例如：
  - Mac：`/Users/你的用户名/musinsa-price-watcher`
  - Windows：`C:\Users\你的用户名\Downloads\musinsa-price-watcher`

---

## 二、第一次安装（只做一次）

### 1. Mac（苹果电脑）

1. 打开「终端」（Launchpad 搜索 Terminal）。
2. 进入项目目录（路径按你自己的实际位置改）：

```bash
cd /Users/你的用户名/musinsa-price-watcher
```

3. 安装依赖：

```bash
pip3 install -r requirements.txt
python3 -m playwright install chromium
```

> 如果 `pip3` 提示找不到，可以试 `python3 -m pip install -r requirements.txt`。

### 2. Windows 电脑

1. 安装 Python 3（如果没有）：从 `https://www.python.org/downloads/` 下载并安装，安装时勾选「Add Python to PATH」。
2. 打开「命令提示符 (cmd)」。
3. 进入项目目录，例如：

```bat
cd C:\Users\你的用户名\Downloads\musinsa-price-watcher
```

4. 安装依赖：

```bat
py -3 -m pip install -r requirements.txt
py -3 -m playwright install chromium
```

---

## 三、配置邮件（可选，但推荐）

1. 用记事本 / VSCode 打开项目里的 `config.py`。
2. 按你的邮箱修改：
   - QQ 邮箱：
     - `MAIL_SMTP = "smtp.qq.com"`
     - `MAIL_USER` 填你的 QQ 邮箱地址
     - `MAIL_PASSWORD` 填 QQ 邮箱的「授权码」（在 QQ 邮箱网页版 → 设置 → 账户 → POP3/IMAP 里开启并获取）
   - 163 邮箱：
     - `MAIL_SMTP = "smtp.163.com"`，其余同理
3. 如果暂时不想收邮件通知，可以把 `MAIL_PASSWORD` 留空，程序仍然可以使用网页，只是不发邮件。

---

## 四、以后每次使用（Mac & Windows 都一样的流程）

> 下面步骤是**每次想用的时候都要做的**。

### 步骤 1：启动程序

在终端 / 命令提示符中：

1. 进入项目目录（举例，按你的实际路径改）：

```bash
cd /路径/到/musinsa-price-watcher
```

2. 启动程序（统一使用 5001 端口）：

```bash
PORT=5001 python3 app.py      # Mac 建议
```

或在 Windows：

```bat
set PORT=5001
py -3 app.py
```

看到类似输出：

```text
 * Running on http://127.0.0.1:5001
```

说明已经启动成功。

### 步骤 2：在浏览器里访问

在浏览器地址栏输入：

```text
http://127.0.0.1:5001
```

你会看到一个中文界面，可以：

- 在「添加商品」里粘贴 무신사 商品链接（例如 `https://www.musinsa.com/products/1090694`）并点击「添加」；
- 在「通知邮箱」里填自己的邮箱并点击「保存」；
- 点击「立即检查一次价格」手动检查一遍。

> 收藏页入口：`https://www.musinsa.com/like/goods`，登录后点进商品，复制浏览器地址栏链接即可。

### 步骤 3：什么时候关掉

- 在使用过程中：**终端窗口要保持打开**，不要关闭，也不要按 `Ctrl + C`。
- 不需要用时：在终端里按 `Ctrl + C` 结束程序，再关闭终端窗口即可。

---

## 五、常见问题

- **看不到网页 / 打不开 127.0.0.1:5001？**
  - 确认终端里有没有正在运行 `app.py`，有 `Running on http://127.0.0.1:5001` 这一行。
  - 如有杀毒软件 / 防火墙拦截，选择允许本地访问。

- **提示端口被占用（port in use）？**
  - 说明本机已经有程序占用了 5000 端口，本项目已经改为优先用 5001。
  - 如果 5001 也被占用，可以在启动前改一下端口，例如：
    - Mac：`PORT=5002 python3 app.py`
    - Windows：`set PORT=5002` 然后 `py -3 app.py`

- **价格不正确？**
  - 程序会优先抓取商品页上显示「쿠폰价（Price__CalculatedPrice…）」这一栏，一般和页面看到的蓝色价格一致。
  - 个别商品若仍有差异，需要开发者根据页面结构再做一次规则调整。

- **多人使用说明**
  - 建议每个人都在自己电脑上单独运行一份本项目，各自有自己的监测列表和邮箱，不会互相影响。
  - 也可以让一台电脑长期打开，把地址 `http://那台电脑的局域网 IP:5001` 分享给同一 Wi‑Fi 下的同事使用。

如在使用过程中遇到任何英文报错，可以把终端里的报错整段截图给开发者，由他帮忙排查。

