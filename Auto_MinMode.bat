@echo off
setlocal
cd /d "%~dp0"

:: 1. Search for Python executable (Blender Workspace, local bin, or system PATH)
set "PY_EXE="
if exist "%~dp0..\blender-5.1.1-windows-x64\5.1\python\bin\python.exe" (
    set "PY_EXE=%~dp0..\blender-5.1.1-windows-x64\5.1\python\bin\python.exe"
) else if exist "%~dp0bin\python\python.exe" (
    set "PY_EXE=%~dp0bin\python\python.exe"
) else (
    where python >nul 2>nul
    if not errorlevel 1 (
        set "PY_EXE=python"
    ) else (
        where py >nul 2>nul
        if not errorlevel 1 (
            set "PY_EXE=py"
        )
    )
)

if "%PY_EXE%"=="" (
    echo [ERROR] Python 3 was not found on your system!
    echo Please install Python from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Check if the required 'vpk' library is installed
"%PY_EXE%" -c "import vpk" >nul 2>nul
if errorlevel 1 (
    echo Installing required Python package 'vpk'...
    "%PY_EXE%" -m pip install vpk
    echo.
)

:: 3. Run auto_minmode.py passing all arguments (dragged files or folders)
"%PY_EXE%" "%~dp0auto_minmode.py" %*

echo.
echo ========================================================
pause
