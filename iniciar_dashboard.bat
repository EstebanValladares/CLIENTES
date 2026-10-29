@echo off
title Centro de Inteligencia Operativa - Grupo Velas
color 0B
cls
echo ======================================================================
echo           CENTRO DE INTELIGENCIA OPERATIVA - GRUPO VELAS
echo ======================================================================
echo.

:: 1. Deteccion inteligente de Python en el sistema
set "PY_CMD=python"
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set "PY_CMD=py"
    ) else (
        color 0C
        echo [ERROR]: Python no esta instalado o no se encuentra en el PATH del sistema.
        echo.
        echo Por favor instala Python 3.10 o superior descargandolo de:
        echo https://www.python.org/downloads/
        echo.
        echo REQUISITO INDISPENSABLE:
        echo En el instalador marca la casilla "Add python.exe to PATH".
        echo.
        pause
        exit /b 1
    )
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

:: 3. Verificacion y auto-instalacion de dependencias
echo [2/4] Verificando dependencias necesarias (FastAPI, Uvicorn, Firebase)...
%PY_CMD% -c "import fastapi, uvicorn, firebase_admin, pydantic, requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [INFO] Detectamos componentes pendientes por instalar.
    echo [INFO] Instalando dependencias de Python automaticamente...
    echo.
    %PY_CMD% -m pip install --upgrade pip --quiet 2>nul
    %PY_CMD% -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        color 0C
        echo.
        echo [ERROR]: No se pudieron instalar las dependencias con pip.
        echo Verifica tu conexion a Internet y vuelve a ejecutar este archivo.
        echo.
        pause
        exit /b 1
    )
    echo [OK] Todas las dependencias se instalaron correctamente.
) else (
    echo [OK] Todas las librerias estan listas.
)
echo.

:: 4. Configuracion de credenciales Aryve (.env) en primer arranque
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
        echo EK10_USER=%USER_EMAIL%
        echo EK10_PASS=%USER_PASS%
        echo EK9_USER=%USER_EMAIL%
        echo EK9_PASS=%USER_PASS%
    ) > ".env"
    echo [OK] Credenciales guardadas localmente en .env con exito.
    echo.
)

:: 5. Lanzamiento del servidor y apertura automatica del navegador
echo [3/4] Iniciando servidor del Dashboard en http://127.0.0.1:8000 ...
echo [INFO] Para apagar el servidor, simplemente cierra esta ventana o presiona CTRL+C.
echo.
start "" "http://127.0.0.1:8000"
%PY_CMD% -m uvicorn api.main:app --host 127.0.0.1 --port 8000
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo [AVISO]: El servidor se detuvo o el puerto 8000 ya esta en uso por otra app.
)
pause
