@echo off
title Organizador de Documentos de Estudiantes
cd /d "%~dp0"
python organizador.py
if errorlevel 1 (
    echo.
    echo No se pudo iniciar. Verifica que Python este instalado.
    pause
)
