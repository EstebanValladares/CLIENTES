@echo off
chcp 65001 > nul
cd /d "%~dp0"
title Centro de Inteligencia Operativa - Grupo Velas
color 0B
cls
echo ======================================================================
echo           CENTRO DE INTELIGENCIA OPERATIVA - GRUPO VELAS
echo ======================================================================
echo.

set "PY_CMD="
for %%V in (312 311 310 313 314 39) do (
    if not defined PY_CMD (
        if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
            "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" -m pip --version >nul 2>&1
            if not errorlevel 1 set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
        )
    )
)
if not defined PY_CMD (
    for /f "delims=" %%I in ('where python.exe 2^>nul') do (
        if not defined PY_CMD (
            echo "%%I" | findstr /i "msys64" >nul
            if errorlevel 1 (
                "%%I" -m pip --version >nul 2>&1
                if not errorlevel 1 set "PY_CMD=%%I"
            )
        )
    )
)
if not defined PY_CMD (
    py -m pip --version >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py"
)
if not defined PY_CMD (
    python -m pip --version >nul 2>&1
    if not errorlevel 1 set "PY_CMD=python"
)

if not defined PY_CMD (
    color 0C
    echo [ERROR]: No se encontro una instalacion valida de Python con pip en este equipo.
    pause
    exit /b 1
)

:: Liberar puerto 8000 si un proceso anterior quedo colgado en segundo plano
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: Sincronizacion limpia con GitHub (Descarga lo nuevo de la Torre)
if exist ".git" (
    echo [1/3] Sincronizando con la ultima version publicada por la Torre...
    git fetch origin main >nul 2>&1
    git reset --hard origin/main >nul 2>&1
    git pull origin main --quiet >nul 2>&1
    for /f "tokens=*" %%H in ('git rev-parse --short HEAD 2^>nul') do set "GIT_COMMIT=%%H"
    echo [OK] Sistema al dia con la Torre: Commit %GIT_COMMIT%
)

:: Dependencias
"%PY_CMD%" -c "import fastapi, uvicorn, pydantic, requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo [2/3] Instalando dependencias de Python...
    "%PY_CMD%" -m pip install -r requirements.txt --quiet
)

:: Iniciar verificador de apertura de navegador (espera a que el servidor responda antes de abrir)
echo [3/3] Iniciando Dashboard en http://127.0.0.1:8000 ...
start /b "" powershell -NoProfile -Command ^
  "$max = 40; " ^
  "for ($i=0; $i -lt $max; $i++) { " ^
  "  Start-Sleep -Milliseconds 300; " ^
  "  try { " ^
  "    $client = New-Object System.Net.Sockets.TcpClient; " ^
  "    $client.Connect('127.0.0.1', 8000); " ^
  "    if ($client.Connected) { " ^
  "      $client.Close(); " ^
  "      Start-Sleep -Milliseconds 400; " ^
  "      Start-Process 'http://127.0.0.1:8000'; " ^
  "      break; " ^
  "    } " ^
  "  } catch {} " ^
  "}"

:: Iniciar servidor FastAPI / Uvicorn
"%PY_CMD%" -m uvicorn api.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 (
    color 0C
    echo.
    echo ======================================================================
    echo [ERROR AL INICIAR]: El servidor no pudo arrancar. Revisa el mensaje arriba.
    echo ======================================================================
    pause
)
