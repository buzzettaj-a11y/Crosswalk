@echo off
REM Crosswalk, started with a visible window.
REM Most people should double-click Crosswalk.vbs instead, which runs the
REM same thing without this window. Use this one when you want to watch it
REM start, or to see an error that scrolled past.
cd /d "%~dp0"
python launch.py
echo.
echo Crosswalk has stopped. You can close this window.
pause
