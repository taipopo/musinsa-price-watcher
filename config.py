# 配置文件 - 请根据你的情况修改

# 邮件通知设置（价格变动时发邮件给你）
# 若暂时不用邮件，可留空 MAIL_PASSWORD，不会发邮件
MAIL_ENABLED = True
MAIL_SMTP = "smtp.qq.com"  # QQ邮箱用 smtp.qq.com，163用 smtp.163.com
MAIL_PORT = 587
MAIL_USER = ""  # 你的邮箱，例如 your@qq.com
MAIL_PASSWORD = ""  # 邮箱的授权码（不是登录密码，需在邮箱设置里开启 SMTP 并获取）
MAIL_FROM_NAME = "무신사 价格监测"

# 价格检查间隔（分钟）
CHECK_INTERVAL_MINUTES = 60

# 是否使用浏览器抓取（若网页用 JavaScript 显示价格，设为 True）
USE_BROWSER = True
