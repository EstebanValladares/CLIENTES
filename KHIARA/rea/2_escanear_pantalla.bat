@echo off
chcp 65001 > nul
title REA Paso 2 - Escanear Pantalla Activa de Aryve

cd /d "%~dp0"

set "PY_EXE=python"

"%PY_EXE%" escanear_rea.py
pause

