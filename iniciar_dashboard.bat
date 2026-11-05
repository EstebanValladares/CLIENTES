@echo off
title Centro de Inteligencia Operativa - Grupo Velas
color 0B
cls
echo ======================================================================
echo           CENTRO DE INTELIGENCIA OPERATIVA - GRUPO VELAS
echo ======================================================================
echo.

:: 1. Deteccion inteligente de Python en el sistema (evitando ejecutables de msys64 sin pip)
set "PY_CMD="

:: A. Probar instalaciones estandar de Python oficial de Windows (Local AppData)
for %%V in (312 311 310 313 314 39) do (
    if not defined PY_CMD (
        if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
            "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" -m pip --version >nul 2>&1
            if not errorlevel 1 set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
        )
    )
)

:: B. Probar en Program Files (instalaciones para todos los usuarios)
if not defined PY_CMD (
    for %%V in (312 311 310 313 314 39) do (
        if not defined PY_CMD (
            if exist "C:\Program Files\Python%%V\python.exe" (
                "C:\Program Files\Python%%V\python.exe" -m pip --version >nul 2>&1
                if not errorlevel 1 set "PY_CMD=C:\Program Files\Python%%V\python.exe"
            )
        )
    )
)

:: C. Probar cada python encontrado en PATH que NO sea de msys64 y que tenga pip funcional
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

:: D. Probar lanzador oficial de Windows (py)
if not defined PY_CMD (
    py -m pip --version >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py"
)

:: E. Ultimo intento con comando generico
if not defined PY_CMD (
    python -m pip --version >nul 2>&1
    if not errorlevel 1 set "PY_CMD=python"
)

if not defined PY_CMD goto :no_python
goto :python_ok

:no_python
color 0C
echo [ERROR]: No se encontro una instalacion valida de Python con pip en este equipo.
echo.
echo Si tienes instalado Git o MSYS2, el sistema detecto un Python interno sin pip.
echo Por favor instala el instalador oficial de Python para Windows (Python 3.10 o superior):
echo https://www.python.org/downloads/
echo.
echo REQUISITO INDISPENSABLE:
echo En el instalador marca la casilla "Add python.exe to PATH".
echo.
pause
exit /b 1

:python_ok
:: 2. Sincronizacion con Git (Blindaje automatico contra caidas)
if exist ".git" (
    echo [1/4] Descargando ultimas actualizaciones desde GitHub...
    git fetch origin main
    git reset --hard origin/main
    git pull origin main
    for /f "tokens=*" %%H in ('git rev-parse --short HEAD 2^>nul') do set "GIT_COMMIT=%%H"
    echo [OK] Sistema sincronizado al ultimo commit de GitHub: Git %GIT_COMMIT%
) else (
    echo [1/4] Repositorio local preparado.
)
echo.

:: 3. Verificacion y auto-instalacion de dependencias
echo [2/4] Verificando dependencias necesarias (FastAPI, Uvicorn, Firebase)...
"%PY_CMD%" -c "import fastapi, uvicorn, pydantic, requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [INFO] Detectamos componentes pendientes por instalar.
    echo [INFO] Instalando dependencias de Python automaticamente...
    echo.
    "%PY_CMD%" -m pip install --upgrade pip --quiet 2>nul
    "%PY_CMD%" -m pip install -r requirements.txt
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
if exist ".env" goto :servidor_start

echo ======================================================================
echo             CONFIGURACION INICIAL DE CREDENCIALES ARYVE
echo ======================================================================
echo [!] Es la primera vez que inicias el sistema en este equipo.
echo Para que los procesos y bots funcionen con tu usuario oficial,
echo por favor ingresa tus credenciales de Grupo Velas.
echo.
echo Tus claves se guardan UNICAMENTE en este equipo y NUNCA se comparten.
echo ----------------------------------------------------------------------
set /p "USER_EMAIL=>> Correo de Grupo Velas (ej. usuario@grupovelas.com): "
set /p "USER_PASS=>> Contrasena de Aryve / Enkontrol: "
echo.
(
    echo # ==============================================================================
    echo # CREDENCIALES LOCALES DEL USUARIO - Protegido por .gitignore
    echo # ==============================================================================
    echo ARYVE_BASE_URL=https://suite.ekloud.net:1445/Aryve/
    echo EK10_USER=%USER_EMAIL%
    echo EK10_PASS=%USER_PASS%
    echo EK9_USER=%USER_EMAIL%
    echo EK9_PASS=%USER_PASS%
) > ".env"
echo [OK] Credenciales guardadas localmente en .env con exito.
echo.

:servidor_start
:: 5. Lanzamiento del servidor y apertura automatica del navegador
echo [3/4] Iniciando servidor del Dashboard en http://127.0.0.1:8000 ...
echo [INFO] Para apagar el servidor, simplemente cierra esta ventana o presiona CTRL+C.
echo.
start "" "http://127.0.0.1:8000"
"%PY_CMD%" -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo [AVISO]: El servidor se detuvo o el puerto 8000 ya esta en uso por otra app.
)
pause
