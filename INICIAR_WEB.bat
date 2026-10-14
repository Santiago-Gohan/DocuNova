@echo off
chcp 65001 >nul
title DocuNova - Web
cd /d "%~dp0webapp"

echo ============================================================
echo   DocuNova - Organizador de documentos (web)
echo ------------------------------------------------------------
echo   Se abrira el navegador en:  http://127.0.0.1:5000
echo   Para detener el servidor:   cierra esta ventana
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] No se encontro Python. Instalalo desde python.org
  pause
  exit /b
)

start "" http://127.0.0.1:5000
python app.py

echo.
echo El servidor se detuvo.
pause
