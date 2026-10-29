@echo off
title Centro de Inteligencia Operativa - Grupo Velas
color 0B
cls
echo ======================================================================
echo           CENTRO DE INTELIGENCIA OPERATIVA - GRUPO VELAS
echo ======================================================================
echo.
echo [1/2] Verificando actualizaciones del sistema en GitHub...
git pull origin main --quiet 2>nul
echo [OK] Sistema sincronizado al dia.
echo.
echo [2/2] Iniciando servidor del Dashboard en http://127.0.0.1:8000 ...
echo.
start "" "http://127.0.0.1:8000"
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
pause
