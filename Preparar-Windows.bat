@echo off
rem Executa a preparacao com politica de execucao liberada SOMENTE para este processo (nao altera o sistema).
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\00-Preparar-Windows.ps1" %*
pause
