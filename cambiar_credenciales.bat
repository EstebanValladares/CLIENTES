@echo off
title Actualizar Credenciales - Grupo Velas
color 0B
cls
echo ======================================================================
echo           ACTUALIZACION DE CREDENCIALES - GRUPO VELAS
echo ======================================================================
echo.
echo Ingresa tus nuevas credenciales de Aryve / Enkontrol.
echo Se guardaran de forma segura en tu equipo (.env).
echo.
set /p "USER_EMAIL=>> Correo de Grupo Velas (ej. usuario@grupovelas.com): "
set /p "USER_PASS=>> Nueva contrasena de Aryve: "
echo.
if "%USER_EMAIL%"=="" (
    echo [ERROR]: El correo no puede estar vacio.
    pause
    exit /b 1
)
(
    echo # ==============================================================================
    echo # CREDENCIALES LOCALES DEL USUARIO (Privado - Protegido por .gitignore)
    echo # ==============================================================================
    echo EK10_USER=%USER_EMAIL%
    echo EK10_PASS=%USER_PASS%
    echo EK9_USER=%USER_EMAIL%
    echo EK9_PASS=%USER_PASS%
) > ".env"
color 0A
echo.
echo [OK] Credenciales actualizadas exitosamente en tu equipo.
echo.
pause
