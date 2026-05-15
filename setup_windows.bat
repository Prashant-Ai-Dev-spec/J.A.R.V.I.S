@echo off
title J.A.R.V.I.S Setup
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   J.A.R.V.I.S  — Setup Script (Windows) ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ from python.org
    pause & exit /b 1
)

echo [1/4] Upgrading pip...
python -m pip install --upgrade pip

echo [2/4] Installing core packages...
pip install anthropic SpeechRecognition pyttsx3 psutil requests pyperclip

echo [3/4] Installing PyAudio...
pip install PyAudio
if errorlevel 1 (
    echo [WARN] PyAudio failed. Trying pipwin...
    pip install pipwin
    pipwin install pyaudio
    if errorlevel 1 (
        echo [WARN] PyAudio install failed. JARVIS will run in text mode.
    )
)

echo [4/4] Installing optional packages...
pip install pyautogui Pillow pygame pytesseract

echo.
echo  ✓ Setup complete!
echo.
echo  NEXT STEPS:
echo  1. Edit jarvis_config.json — add your API keys and email
echo  2. Run: python jarvis.py --mode hybrid
echo     (or: python jarvis.py --mode text   — no microphone needed)
echo.
pause
