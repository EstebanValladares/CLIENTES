@echo off
title Centro de Inteligencia Operativa - Grupo Velas
color 0B
cls
echo ======================================================================
echo           CENTRO DE INTELIGENCIA OPERATIVA - GRUPO VELAS
echo ======================================================================
echo.

:: Asegurar ubicacion en la carpeta local del proyecto
cd /d "%~dp0"

:: 1. Deteccion de Python
set PY_EXE=
py -3 -V >nul 2>&1 && set PY_EXE=py -3
if "%PY_EXE%"=="" (
    python -V >nul 2>&1 && set PY_EXE=python
)
if "%PY_EXE%"=="" (
    if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set PY_EXE="%LocalAppData%\Programs\Python\Python312\python.exe"
    if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set PY_EXE="%LocalAppData%\Programs\Python\Python311\python.exe"
    if exist "%LocalAppData%\Programs\Python\Python310\python.exe" set PY_EXE="%LocalAppData%\Programs\Python\Python310\python.exe"
)

if "%PY_EXE%"=="" (
    color 0C
    echo [ERROR]: No se encontro Python instalado en el sistema.
    echo Por favor instala Python 3.10 o superior marcando "Add to PATH".
    echo.
    pause
    exit /b 1
)

:: 2. Actualizacion con GitHub si existe .git
if exist ".git" (
    echo [1/4] Verificando actualizaciones en GitHub...
    git pull origin main --quiet 2>nul
    echo [OK] Sistema al dia con la nube.
) else (
    echo [1/4] Repositorio local preparado.
)
echo.

:: 3. Entorno Virtual .venv
echo [2/4] Verificando entorno virtual (.venv)...
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creando entorno virtual aislado...
    %PY_EXE% -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
    color 0C
    echo [ERROR]: No se pudo crear el entorno virtual .venv.
    pause
    exit /b 1
)

:: Verificar e instalar librerias en .venv
.venv\Scripts\python.exe -c "import fastapi, uvicorn, firebase_admin" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Instalando dependencias necesarias...
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        color 0C
        echo [ERROR]: Fallo la instalacion de dependencias. Revisa tu conexion a Internet.
        pause
        exit /b 1
    )
)
echo [OK] Entorno virtual listo.
echo.

:: 4. Credenciales .env
if not exist ".env" (
    echo ======================================================================
    echo             CONFIGURACION INICIAL DE CREDENCIALES ARYVE
    echo ======================================================================
    echo [!] Es la primera vez que inicias el sistema en este equipo.
    echo Ingrese sus credenciales oficiales de Grupo Velas:
    echo.
    set /p USER_EMAIL=">> Correo de Grupo Velas (ej. usuario@grupovelas.com): "
    set /p USER_PASS=">> Contrasena de Aryve / Enkontrol: "
    echo.
    echo EK10_USER=%USER_EMAIL%> .env
    echo EK10_PASS=%USER_PASS%>> .env
    echo EK9_USER=%USER_EMAIL%>> .env
    echo EK9_PASS=%USER_PASS%>> .env
    echo [OK] Credenciales guardadas en .env.
    echo.
) else (
    echo [OK] Credenciales personales detectadas (.env cargado).
    echo.
)

:: 5. Servidor y Navegador
echo [3/4] Iniciando servidor del Dashboard en http://127.0.0.1:8000 ...
echo [INFO] Para detener el sistema presione CTRL+C o cierre esta ventana.
echo.
start "" "http://127.0.0.1:8000"
.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
echo.
pause
