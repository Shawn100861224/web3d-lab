@echo off
setlocal
title web3d-lab 本地网站启动器

set "ROOT=D:\lab\web3d-lab"
set "PY=%ROOT%\backend\.venv\Scripts\python.exe"
set "NPM=C:\Users\Shawn\AppData\Local\hermes\node\npm.cmd"
set "LOG=%ROOT%\_startup.log"

echo ============================================
echo   web3d-lab 本地网站 一键启动
echo   后端 :8000   前端 :5173
echo ============================================
echo.

> "%LOG%" echo ==== 启动 %date% %time% ====
>>"%LOG%" echo PY=%PY%
>>"%LOG%" echo NPM=%NPM%

if not exist "%PY%" (
  echo [错误] 找不到后端虚拟环境：%PY%
  >>"%LOG%" echo 错误：找不到 python
  pause
  exit /b 1
)
if not exist "%NPM%" (
  echo [错误] 找不到 npm：%NPM%
  >>"%LOG%" echo 错误：找不到 npm
  pause
  exit /b 1
)

echo [1/3] 启动后端 uvicorn :8000 ...
powershell -NoProfile -Command "Start-Process -WindowStyle Minimized -FilePath '%PY%' -ArgumentList '-m','uvicorn','asgi:app','--host','127.0.0.1','--port','8000' -WorkingDirectory '%ROOT%\backend'"
>>"%LOG%" echo 后端启动退出码=%ERRORLEVEL%

echo [2/3] 启动前端 vite :5173 ...
powershell -NoProfile -Command "Start-Process -WindowStyle Minimized -FilePath '%NPM%' -ArgumentList 'run','dev' -WorkingDirectory '%ROOT%\frontend'"
>>"%LOG%" echo 前端启动退出码=%ERRORLEVEL%

echo [3/3] 等前端就绪（最多 40 秒）...
set /a N=0
:wait
timeout /t 2 /nobreak >nul
set /a N+=2
netstat -ano | findstr ":5173" | findstr LISTENING >nul 2>&1
if %ERRORLEVEL%==0 goto ready
if %N% GEQ 40 goto timeout
goto wait

:ready
>>"%LOG%" echo 前端就绪，用时 %N% 秒
echo 服务已就绪，打开浏览器...
start "" "http://127.0.0.1:5173/"
goto done

:timeout
>>"%LOG%" echo 超时：%N% 秒内 5173 未监听
echo [警告] 前端 40 秒内没起来，请看日志：%LOG%
start "" "%LOG%"

:done
echo.
echo 说明：
echo   本地调试地址（需本机服务在跑）：http://127.0.0.1:5173
echo   给别人看的线上地址（不需本机开机）：
echo     https://shawn100861224.github.io/web3d-lab/
echo   停止服务：双击 stop-local.bat
echo.
echo 按任意键关闭本窗口（服务继续在后台跑）...
pause >nul
endlocal
