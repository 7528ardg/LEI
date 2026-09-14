@echo off
chcp 936 >nul
cd /d "%~dp0"
set PORT=8000
echo.
echo  Local server: http://127.0.0.1:%PORT%/
echo  Keep this window open; close it to stop the server.
echo.
start "" http://127.0.0.1:%PORT%/index.html
where python >nul 2>nul && (python -m http.server %PORT% & goto :eof)
where py >nul 2>nul && (py -3 -m http.server %PORT% & goto :eof)
echo Python not found in PATH. Install Python, or open the HTML from a local web server.
pause
