@echo off
chcp 65001 >nul
cd /d %~dp0
echo Mistral Pipeline
python pipeline_worker.py mistral
pause
