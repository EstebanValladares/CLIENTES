@echo off
setlocal
title Centro de Inteligencia Operativa - Grupo Velas
color 0B
cls
echo ======================================================================
echo           CENTRO DE INTELIGENCIA OPERATIVA - GRUPO VELAS
echo ======================================================================
echo.

cd /d "%~dp0"

:: 1. Deteccion de Python oficial de Windows
set "PY_EXE="

:: Prueba 1: Launcher 'py -3'
py -3 -V >nul 2>&1
if not errorlevel 1 set "PY_EXE=py -3"

:: Prueba 2: Rutas estandar de Python oficial en Windows
if "%PY_EXE%"=="" (
    if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PY_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
    if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PY_EXE=%LocalAppData%\Programs\Python\Python311\python.exe"
    if exist "%LocalAppData%\Programs\Python\Python310\python.exe" set "PY_EXE=%LocalAppData%\Programs\Python\Python310\python.exe"
    if exist "C:\Python312\python.exe" set "PY_EXE=C:\Python312\python.exe"
    if exist "C:\Python311\python.exe" set "PY_EXE=C:\Python311\python.exe"
    if exist "C:\Python310\python.exe" set "PY_EXE=C:\Python310\python.exe"
)

:: Prueba 3: 'python' en PATH
if "%PY_EXE%"=="" (
    python -V >nul 2>&1
    if not errorlevel 1 set "PY_EXE=python"
)

if "%PY_EXE%"=="" (
    color 0C
    echo [ERROR]: No se encontro Python instalado en este equipo.
    echo Por favor descargue e instale Python de: https://www.python.org/downloads/
    echo Recuerde marcar "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

:: 2. Sincronizacion con Git si existe .git
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

if not exist ".venv" (
    echo [INFO] Creando entorno virtual aislado...
    %PY_EXE% -m venv .venv
)

:: Localizar el ejecutable python del venv (Scripts en Windows, bin en entornos POSIX)
set "V_PY="
if exist ".venv\Scripts\python.exe" set "V_PY=.venv\Scripts\python.exe"
if "%V_PY%"=="" if exist ".venv\bin\python.exe" set "V_PY=.venv\bin\python.exe"
if "%V_PY%"=="" if exist ".venv\bin\python" set "V_PY=.venv\bin\python"

if "%V_PY%"=="" (
    color 0C
    echo [ERROR]: El entorno virtual .venv no tiene interprete valido.
    echo Intentando ejecutar directamente con: %PY_EXE%
    set "V_PY=%PY_EXE%"
)

:: Verificar dependencias e instalarlas si faltan
%V_PY% -c "import fastapi, uvicorn, firebase_admin" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Instalando dependencias necesarias (FastAPI, Uvicorn, Firebase)...
    %V_PY% -m pip install -r requirements.txt
    if errorlevel 1 (
        color 0C
        echo [ERROR]: No se pudieron instalar las dependencias.
        echo Verifique su conexion a internet.
        pause
        exit /b 1
    )
    echo [OK] Dependencias instaladas con exito.
) else (
    echo [OK] Entorno virtual listo y verificado.
)
echo.

:: 4. Configuracion de credenciales .env (SOLO PRIMER ARRANQUE)
if not exist ".env" (
    echo ======================================================================
    echo             CONFIGURACION INICIAL DE CREDENCIALES ARYVE
    echo ======================================================================
    echo [!] Es la primera vez que inicias el sistema en este equipo.
    echo Por favor ingresa tus credenciales oficiales de Grupo Velas:
    echo.
    set /p "USER_EMAIL=>> Correo de Grupo Velas (ej. usuario@grupovelas.com): "
    set /p "USER_PASS=>> Contrasena de Aryve / Enkontrol: "
    echo.
    (
        echo EK10_USER=%USER_EMAIL%
        echo EK10_PASS=%USER_PASS%
        echo EK9_USER=%USER_EMAIL%
        echo EK9_PASS=%USER_PASS%
    ) > ".env"
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
%V_PY% -m uvicorn api.main:app --host 127.0.0.1 --port 8000

echo.
echo El servidor se ha detenido.
pause
