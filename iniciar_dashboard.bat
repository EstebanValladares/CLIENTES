@echo off
title Centro de Inteligencia Operativa - Grupo Velas
color 0B
cls
echo ======================================================================
echo           CENTRO DE INTELIGENCIA OPERATIVA - GRUPO VELAS
echo ======================================================================
echo.

:: 1. Verificacion de Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR]: Python no esta instalado o no se encuentra en el PATH del sistema.
    echo.
    echo Por favor instala Python 3.10 o superior descargandolo de python.org
    echo y asegurate de marcar la casilla "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

:: 2. Sincronizacion opcional con Git
if exist ".git" (
    echo [1/3] Verificando actualizaciones del sistema en GitHub...
    git pull origin main --quiet 2>nul
    echo [OK] Sistema al dia con la nube.
) else (
    echo [1/3] Repositorio local preparado.
)
echo.

:: 3. Verificacion y auto-instalacion de librerias necesarias
echo [2/3] Verificando librerias del sistema (FastAPI, Uvicorn, Firebase)...
python -c "import fastapi, uvicorn, firebase_admin, pydantic, requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [INFO] Detectamos que faltan componentes para ejecutar la aplicacion.
    echo [INFO] Instalando dependencias automaticamente... (espera un momento)
    echo.
    python -m pip install --upgrade pip --quiet 2>nul
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        color 0C
        echo.
        echo [ERROR]: No se pudieron instalar las librerias con pip.
        echo Revisa tu conexion a Internet y vuelve a ejecutar este archivo.
        echo.
        pause
        exit /b 1
    )
    echo [OK] Todas las dependencias se instalaron correctamente.
) else (
    echo [OK] Dependencias listas.
)
echo.

:: 4. Lanzamiento del servidor y apertura automatica del navegador
echo [3/3] Iniciando servidor del Dashboard en http://127.0.0.1:8000 ...
echo [INFO] Presiona CTRL + C en esta ventana cuando desees apagar el servidor.
echo.
start "" "http://127.0.0.1:8000"
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo [AVISO]: El servidor se detuvo o el puerto 8000 ya esta en uso.
)
pause
