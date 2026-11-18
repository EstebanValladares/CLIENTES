@echo off
chcp 65001 > nul
title REA Paso 1 - Abrir Aryve en Modo Depuracion (Puerto 9222)

cd /d "%~dp0"

set "PY_EXE=python"

"%PY_EXE%" 1_abrir_aryve_rea.py
pause

