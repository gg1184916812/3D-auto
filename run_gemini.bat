@echo off
chcp 65001 >nul
cd /d %~dp0
echo Mistral Pipeline
echo 請先設定環境變數:
echo set GEMINI_KEY=你的GEMINI_API_KEY
echo 然後再執行這個腳本
pause
