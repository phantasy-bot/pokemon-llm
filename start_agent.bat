@echo off
setlocal EnableDelayedExpansion

echo 🚀 Pokemon LLM Agent Launcher
echo =============================

REM Initialize conda for this shell
call "%USERPROFILE%\miniconda3\Scripts\activate.bat" "%USERPROFILE%\miniconda3"

REM 1. Check if pokemon-llm environment exists, create if needed
conda info --envs | findstr /C:"pokemon-llm" > nul 2>&1
if errorlevel 1 (
    echo 📦 Creating conda environment 'pokemon-llm'...
    call conda create -n pokemon-llm python=3.10 -y
    if errorlevel 1 (
        echo ❌ Failed to create conda environment
        goto cleanup
    )
)

REM 2. Activate the environment
echo 🐍 Activating conda environment 'pokemon-llm'...
call conda activate pokemon-llm
if errorlevel 1 (
    echo ❌ Failed to activate conda environment
    goto cleanup
)

REM 3. Check if Python dependencies are installed, install if needed
python -c "import PIL, openai, websockets" > nul 2>&1
if errorlevel 1 (
    echo 📦 Installing Python dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Failed to install Python dependencies
        goto cleanup
    )
)

REM 4. Check if node_modules exists, install if needed
cd pokemon-ui
if not exist "node_modules\" (
    echo 📦 Installing UI dependencies...
    call npm install
    if errorlevel 1 (
        echo ❌ npm install failed
        cd ..
        goto cleanup
    )
)

REM 5. Start Frontend (in background)
echo 🎨 Starting Pokemon UI...
start /B cmd /c "npm run dev > ..\ui.log 2>&1"
cd ..
echo    Logs: ui.log

REM 6. Wait for Frontend to be ready
echo ⏳ Waiting for UI to be ready at http://localhost:5173...
set MAX_RETRIES=30
set COUNT=0

:wait_loop
curl -s http://localhost:5173 > nul 2>&1
if !ERRORLEVEL! EQU 0 goto ui_ready
timeout /t 1 /nobreak > nul
set /a COUNT+=1
if !COUNT! GEQ %MAX_RETRIES% (
    echo ❌ Frontend failed to start in 30 seconds. Check ui.log.
    goto cleanup
)
goto wait_loop

:ui_ready
echo ✅ UI is ready!

REM 7. Open Browser
echo 🌍 Opening Browser...
start http://localhost:5173

REM 8. Start Backend
echo 🤖 Starting Agent Backend...
python run.py --auto

:cleanup
echo 🛑 Shutting down...
REM Kill any npm processes running on port 5173
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /F /PID %%a > nul 2>&1
)
endlocal
