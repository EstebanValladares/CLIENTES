@echo off
setlocal EnableDelayedExpansion
title Centro de Inteligencia Operativa - Grupo Velas
color 0B
cls
echo ======================================================================
echo           CENTRO DE INTELIGENCIA OPERATIVA - GRUPO VELAS
echo ======================================================================
echo.

:: Asegurar que el directorio de trabajo sea exactamente la carpeta del script
cd /d "%~dp0"

:: 1. Deteccion inteligente de Python con soporte para pip y venv
:: Priorizamos Python oficial de Windows o launcher 'py' para evitar entornos truncados como msys64
set "PY_CMD="

:: Prueba 1: Launcher 'py -3' (Python Launcher oficial de Windows)
py -3 -c "import sys; sys.exit(0)" >nul 2>&1
if %errorlevel% equ 0 (
    py -3 -m pip --version >nul 2>&1
    if !errorlevel! equ 0 set "PY_CMD=py -3"
)

:: Prueba 2: Comando 'python' si tiene pip funcional
if not defined PY_CMD (
    python -c "import sys; sys.exit(0)" >nul 2>&1
    if !errorlevel! equ 0 (
        python -m pip --version >nul 2>&1
        if !errorlevel! equ 0 set "PY_CMD=python"
    )
)

:: Prueba 3: Ruta directa en AppData del usuario
if not defined PY_CMD (
    if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
        set "PY_CMD="%LocalAppData%\Programs\Python\Python312\python.exe""
    ) else if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
        set "PY_CMD="%LocalAppData%\Programs\Python\Python311\python.exe""
    ) else if exist "%LocalAppData%\Programs\Python\Python310\python.exe" (
        set "PY_CMD="%LocalAppData%\Programs\Python\Python310\python.exe""
    ) else if exist "%LocalAppData%\Programs\Python\Python314\python.exe" (
        set "PY_CMD="%LocalAppData%\Programs\Python\Python314\python.exe""
    )
)

if not defined PY_CMD (
    color 0C
    echo [ERROR]: No se detecto una instalacion estandar de Python con pip habilitado.
    echo.
    echo Por favor instala Python descargandolo de:
    echo https://www.python.org/downloads/
    echo.
    echo REQUISITO INDISPENSABLE EN EL INSTALADOR:
    echo [X] Marcar la casilla "Add python.exe to PATH"
    echo.
    pause
    exit /b 1
)

:: 2. Sincronizacion con Git (si esta enlazado al repositorio remoto)
if exist ".git" (
    echo [1/4] Verificando actualizaciones en GitHub...
    git pull origin main --quiet 2>nul
    echo [OK] Sistema al dia con la nube.
) else (
    echo [1/4] Repositorio local preparado.
)
echo.

:: 3. Entorno Virtual Aislado (.venv)
:: Creamos y usamos un .venv local para que NO contamine ni sature el Python global de tu companera
echo [2/4] Verificando entorno virtual aislado (.venv)...
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creando entorno virtual aislado en .venv ...
    %PY_CMD% -m venv .venv
    if !errorlevel! neq 0 (
        color 0C
        echo [ERROR]: No se pudo crear el entorno virtual .venv.
        pause
        exit /b 1
    )
    echo [OK] Entorno virtual creado exitosamente.
)

set "VENV_PY=.venv\Scripts\python.exe"

:: Comprobar si las librerias estan instaladas en el .venv
%VENV_PY% -c "import fastapi, uvicorn, firebase_admin, pydantic, requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Instalando dependencias necesarias en .venv (FastAPI, Uvicorn, Firebase)...
    %VENV_PY% -m pip install --upgrade pip --quiet 2>nul
    %VENV_PY% -m pip install -r requirements.txt
    if !errorlevel! neq 0 (
        color 0C
        echo.
        echo [ERROR]: No se pudieron instalar las dependencias en .venv.
        echo Verifica tu conexion a Internet y vuelve a ejecutar.
        echo.
        pause
        exit /b 1
    )
    echo [OK] Dependencias instaladas correctamente en .venv.
) else (
    echo [OK] Entorno virtual listo y verificado.
)
echo.

:: 4. Configuracion de credenciales Aryve (.env) - SOLO SE PIDE UNA VEZ
if not exist ".env" (
    echo ======================================================================
    echo             CONFIGURACION INICIAL DE CREDENCIALES ARYVE
    echo ======================================================================
    echo [!] Es la primera vez que inicias el sistema en este equipo.
    echo Para que los procesos y bots funcionen con tu usuario oficial,
    echo por favor ingresa tus credenciales de Grupo Velas.
    echo.
    echo (Tus claves se guardan UNICAMENTE en este equipo y NUNCA se comparten)
    echo ----------------------------------------------------------------------
    set /p "USER_EMAIL=>> Correo de Grupo Velas (ej. usuario@grupovelas.com): "
    set /p "USER_PASS=>> Contrasena de Aryve / Enkontrol: "
    echo.
    (
        echo # ==============================================================================
        echo # CREDENCIALES LOCALES DEL USUARIO (Privado - Protegido por .gitignore)
        echo # ==============================================================================
        echo EK10_USER=!USER_EMAIL!
        echo EK10_PASS=!USER_PASS!
        echo EK9_USER=!USER_EMAIL!
        echo EK9_PASS=!USER_PASS!
    ) > "%~dp0.env"
    echo [OK] Credenciales guardadas localmente en .env con exito.
    echo.
) else (
    echo [OK] Credenciales personales detectadas (.env cargado).
)
echo.

:: 5. Lanzamiento del servidor y apertura automatica del navegador
echo [3/4] Iniciando servidor del Dashboard en http://127.0.0.1:8000 ...
echo [INFO] Para apagar el servidor, simplemente cierra esta ventana o presiona CTRL+C.
echo.
start "" "http://127.0.0.1:8000"
%VENV_PY% -m uvicorn api.main:app --host 127.0.0.1 --port 8000
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo [AVISO]: El servidor se detuvo o el puerto 8000 ya esta en uso por otra app.
)
pause
