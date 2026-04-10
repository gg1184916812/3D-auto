# Google Colab Ollama 服務器
# 1. 開啟 https://colab.new
# 2. 貼上這段程式碼
# 3. 執行

# 安裝 zstd 和 ollama
!apt-get update && apt-get install -y zstd
!curl -fsSL https://ollama.com/install.sh | sh

# 啟動服務
import subprocess
import time
subprocess.Popen(["ollama", "serve", "--host", "0.0.0.0"])
time.sleep(3)

# 安裝模型
print("安裝模型中...")
subprocess.run(["ollama", "pull", "llama3.2"])
print("模型安裝完成!")

# 安裝 localtunnel
!npm install -g localtunnel

# 啟動 tunnel
print("\n啟動 tunnel...")
tunnel_process = subprocess.Popen(["lt", "--port", "11434", "--subdomain", "你的名字-ollama"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# 等幾秒
time.sleep(5)

print("="*60)
print(" LocalTunnel 已啟動!")
print(" 請用瀏覽器訪問: https://your-name-ollama.loca.lt")
print(" 密碼是: ollama")
print("="*60)
print("\n在本地執行:")
print("set OLLAMA_URL=https://your-name-ollama.loca.lt")
print("set OLLAMA_PASSWORD=ollama")
print("python pipeline_worker.py ollama")
print("\n保持這個分頁開著!")
