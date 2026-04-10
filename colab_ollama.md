# Google Colab Ollama 服務器
# 1. 開啟 https://colab.new
# 2. 貼上這段程式碼
# 3. 執行

# 安裝 Ollama
!curl -fsSL https://ollama.com/install.sh | sh

# 啟動 Ollama 服務器 (CPU 模式)
import subprocess
import os
import time

# 在背景啟動 Ollama
subprocess.Popen(["ollama", "serve", "--host", "0.0.0.0"])

# 等服務啟動
time.sleep(3)

# 安裝模型 (CPU 版本)
print("正在安裝模型...")
subprocess.run(["ollama", "pull", "llama3.2"])
print("模型安裝完成!")

# 安裝 ngrok
!pip install pyngrok -q

# 設定 ngrok (你需要先去 https://ngrok.com 拿免費 Token)
NGROK_TOKEN = "你的NGROK_TOKEN"  # <-- 替換這裡

from pyngrok import ngrok

# 設定 token
ngrok.set_auth_token(NGROK_TOKEN)

# 建立 tunnel 到 Ollama port 11434
tunnel = ngrok.connect(11434, "tcp")

# 取得 public URL
public_url = tunnel.public_url
print(f"\n========================================")
print(f"Ollama 服務已啟動!")
print(f"連接 URL: {public_url}")
print(f"========================================")
print(f"\n在本地電腦執行:")
print(f"set OLLAMA_URL={public_url}")
print(f"python pipeline_worker.py ollama")

# 保持連接
print("\n保持這個分頁開著，直到完成！")
