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

:: 1. Deteccion de Python
set "PY=py -3"
py -3 -V >nul 2>&1
if errorlevel 1 (
    set "PY=python"
    python -V >nul 2>&1
    if errorlevel 1 (
        if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
            set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
        ) else if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
            set "PY=%LocalAppData%\Programs\Python\Python311\python.exe"
        ) else if exist "%LocalAppData%\Programs\Python\Python310\python.exe" (
            set "PY=%LocalAppData%\Programs\Python\Python310\python.exe"
        ) else (
            color 0C
            echo [ERROR]: No se encontro Python en este equipo.
            echo Descarguelo de: https://www.python.org/downloads/
            echo IMPORTANTE: Marque "Add python.exe to PATH".
            echo.
            pause
            exit /b 1
        )
    )
)

:: 2. Sincronizacion con Git si existe .git
if exist ".git" (
    echo [1/3] Verificando actualizaciones en GitHub...
    git pull origin main --quiet 2>nul
    echo [OK] Sistema al dia con la nube.
) else (
    echo [1/3] Carpeta local preparada.
)
echo.

:: 3. Verificacion de dependencias (FastAPI, Uvicorn, Firebase)
echo [2/3] Verificando librerias del sistema...
%PY% -c "import fastapi, uvicorn, firebase_admin, pydantic, requests" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Instalando componentes requeridos con pip...
    %PY% -m pip install -r requirements.txt
    if errorlevel 1 (
        color 0C
        echo [ERROR]: No se pudieron instalar las librerias. Verifique su internet.
        pause
        exit /b 1
    )
)
echo [OK] Librerias verificadas correctamente.
echo.

:: 4. Credenciales de Grupo Velas (.env)
if not exist ".env" (
    echo ======================================================================
    echo             CONFIGURACION INICIAL DE CREDENCIALES ARYVE
    echo ======================================================================
    echo [!] Es la primera vez que inicias el sistema en este equipo.
    echo Ingrese sus credenciales oficiales de Grupo Velas:
    echo.
    set /p "USER_EMAIL=>> Correo de Grupo Velas: "
    set /p "USER_PASS=>> Contrasena de Aryve: "
    echo.
    call :GUARDAR_ENV
    echo [OK] Credenciales guardadas con exito.
    echo.
) else (
    echo [OK] Credenciales personales detectadas (.env cargado).
    echo.
)

:: 5. Arrancar Dashboard y abrir navegador
echo [3/3] Iniciando servidor del Dashboard en http://127.0.0.1:8000 ...
echo [INFO] Para detener el sistema presione CTRL+C o cierre esta ventana.
echo.
start "" "http://127.0.0.1:8000"
%PY% -m uvicorn api.main:app --host 127.0.0.1 --port 8000
echo.
echo El servidor se ha detenido.
pause
exit /b 0

:GUARDAR_ENV
(
    echo EK10_USER=%USER_EMAIL%
    echo EK10_PASS=%USER_PASS%
    echo EK9_USER=%USER_EMAIL%
    echo EK9_PASS=%USER_PASS%
) > .env
exit /b 0
