@echo off
title Centro de Inteligencia Operativa - Grupo Velas
color 0B
cls
cd /d "%~dp0"

echo ======================================================================
echo           CENTRO DE INTELIGENCIA OPERATIVA - GRUPO VELAS
echo ======================================================================
echo.

:: Git pull opcional si existe
if exist ".git" (
    echo [1/2] Verificando actualizaciones en GitHub...
    git pull origin main --quiet 2>nul
    echo [OK] Sistema al dia.
    echo.
)

:: Lanzar con Python
echo [2/2] Iniciando sistema...
py -3 arrancar.py 2>nul
if errorlevel 1 (
    python arrancar.py
)

if errorlevel 1 (
    color 0C
    echo.
    echo [ERROR]: No se pudo iniciar Python.
    echo Asegurese de tener Python instalado desde https://www.python.org/downloads/
    echo marcando "Add python.exe to PATH".
    echo.
    pause
)
