@echo off
rem Abre o painel Xiaomi TV Manager com um Python que existe de verdade.
rem Ordem: data\python.txt (gravado pelo instalador) > Python do usuario > Program Files > PATH.
cd /d "%~dp0"
set "APP=%~dp0app\xiaomi_tv_manager.py"
set "PYW="

if exist "%~dp0data\python.txt" set /p PYW=<"%~dp0data\python.txt"
if defined PYW if exist "%PYW%" goto :abrir
set "PYW="

for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%~D\pythonw.exe" set "PYW=%%~D\pythonw.exe"
if defined PYW goto :abrir
for /d %%D in ("%ProgramFiles%\Python3*") do if exist "%%~D\pythonw.exe" set "PYW=%%~D\pythonw.exe"
if defined PYW goto :abrir
for /f "delims=" %%P in ('where pythonw.exe 2^>nul ^| findstr /v /i "WindowsApps"') do if not defined PYW set "PYW=%%P"
if defined PYW goto :abrir

echo.
echo  Nenhum Python funcional foi encontrado neste computador.
echo  Rode o INSTALAR.bat (ele instala o Python automaticamente).
echo.
pause
exit /b 1

:abrir
start "" "%PYW%" "%APP%"
exit /b 0
