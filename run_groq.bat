@echo off
chcp 65001 >nul
cd /d %~dp0
echo GROQ Pipeline
python pipeline_worker.py groq
pause
