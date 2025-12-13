@echo off
echo Starting Pokemon LLM Agent + UI...

:: Auto-install missing dependencies
echo Installing/updating dependencies...
pip install --upgrade -r requirements.txt
echo.

:: Start the Python Agent in a new window
start "Pokemon Agent" cmd /k "python run.py --auto"

:: Start the UI in a new window
start "Pokemon UI" cmd /k "cd pokemon-ui && npm run dev"

:: Wait a bit for servers to start then open browser
timeout /t 5
start http://localhost:5173

echo.
echo Agent and UI requested to start.
echo Agent running in separate window.
echo UI running in separate window.
echo.
pause
