@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto dependencies

echo Preparando o ambiente Python...
set "CIRCULA_PYTHON="
for %%P in ("%LocalAppData%\Programs\Python\Python312\python.exe" "%LocalAppData%\Programs\Python\Python313\python.exe" "%LocalAppData%\Programs\Python\Python311\python.exe") do if not defined CIRCULA_PYTHON if exist "%%~P" set "CIRCULA_PYTHON=%%~P"
if defined CIRCULA_PYTHON (
  "%CIRCULA_PYTHON%" -m venv .venv
) else (
  py -3 -m venv .venv
)
if not exist ".venv\Scripts\python.exe" goto failure

:dependencies
".venv\Scripts\python.exe" -c "import flask, flask_sqlalchemy, flask_wtf, psycopg, dotenv, tzdata" >nul 2>&1
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto failure
)
echo.
echo Abra http://127.0.0.1:5000 no navegador.
echo Para encerrar, pressione Ctrl+C nesta janela.
echo.
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto failure
exit /b 0

:failure
echo.
echo Nao foi possivel iniciar. Confira o Python e siga o README.md.
pause
exit /b 1
