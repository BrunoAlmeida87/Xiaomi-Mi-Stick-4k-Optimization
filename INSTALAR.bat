@echo off
rem Instalacao completa em um clique. Nao altera antivirus, firewall nem politicas do Windows.
title Xiaomi TV Manager - Instalacao
cd /d "%~dp0"
if not exist "%~dp0scripts\Instalar.ps1" (
  echo.
  echo  Parece que voce abriu este arquivo de dentro do ZIP.
  echo  Clique com o botao direito no ZIP, escolha "Extrair tudo..." e rode o INSTALAR.bat da pasta extraida.
  echo.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Instalar.ps1"
echo.
pause
