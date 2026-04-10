@echo off
chcp 65001 >nul
cd /d %~dp0
set OLLAMA_URL=https://few-experts-find.loca.lt
set OLLAMA_PASSWORD=ollama
echo Ollama Pipeline (Colab LocalTunnel)
echo URL: %OLLAMA_URL%
python pipeline_worker.py ollama
pause
