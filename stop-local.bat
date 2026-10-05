@echo off
title web3d-lab 停止本地服务

echo 正在停止本机的 8000（后端）与 5173（前端）...

for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":5173" ^| findstr LISTENING') do (
  echo   结束 5173 的进程 PID %%P
  taskkill /PID %%P /F >nul 2>&1
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8000" ^| findstr LISTENING') do (
  echo   结束 8000 的进程 PID %%P
  taskkill /PID %%P /F >nul 2>&1
)

echo.
echo 已停止（提示"没有找到"说明本来就没在跑）。
echo 线上地址不受影响：https://shawn100861224.github.io/web3d-lab/
pause
