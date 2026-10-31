@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys;sys.exit(0 if sys.version_info >= (3,12) else 1)" >nul 2>nul
    if not errorlevel 1 (
        py -3 server.py --open-browser
        goto finished
    )
)
where python >nul 2>nul
if not errorlevel 1 (
    python -c "import sys;sys.exit(0 if sys.version_info >= (3,12) else 1)" >nul 2>nul
    if not errorlevel 1 (
        python server.py --open-browser
        goto finished
    )
)
echo Python 3.12 veya ustu gerekli.
echo https://www.python.org/downloads/ adresinden Python kurun.
echo Kurulumda Add Python to PATH secenegini isaretleyin.
:finished
echo.
echo Uygulama durdu. Bu pencereyi kapatabilirsiniz.
pause
