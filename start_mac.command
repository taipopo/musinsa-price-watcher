#!/bin/bash
# 一键启动：Mac 版

# 切到脚本所在目录（项目根目录）
cd "$(dirname "$0")"

# 使用固定端口 5001
export PORT=5001

echo "正在启动 무신사 收藏价格监测..."
echo "启动后请在浏览器打开： http://127.0.0.1:5001"
echo

# 运行应用
python3 app.py

echo
echo "程序已退出，可以关闭此窗口。"
read -r -p "按回车键关闭..." _

