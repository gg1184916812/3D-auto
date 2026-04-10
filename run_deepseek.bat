@echo off
chcp 65001 >nul
cd /d %~dp0
echo DeepSeek Pipeline
python pipeline_worker.py deepseek
pause
