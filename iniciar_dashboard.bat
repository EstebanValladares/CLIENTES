@echo off
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

:: Sincronizacion inicial con Git
if exist ".git" (
    echo [1/3] Sincronizando con la ultima version de GitHub...
    git fetch origin main
    git reset --hard origin/main
    git pull origin main
    for /f "tokens=*" %%H in ('git rev-parse --short HEAD 2^>nul') do set "GIT_COMMIT=%%H"
    echo [OK] Sistema al dia: Git %GIT_COMMIT%
)

:: Dependencias
"%PY_CMD%" -c "import fastapi, uvicorn, pydantic, requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo [2/3] Instalando dependencias de Python...
    "%PY_CMD%" -m pip install -r requirements.txt --quiet
)

:: Iniciar servidor
echo [3/3] Iniciando Dashboard en http://127.0.0.1:8000 ...
start "" "http://127.0.0.1:8000"
"%PY_CMD%" -m uvicorn api.main:app --host 127.0.0.1 --port 8000
pause
