@echo off
echo ======================================================================
echo   REGISTERING DALAL STREET 8:45 AM AUTO-SCAN (WINDOWS TASK SCHEDULER)
echo ======================================================================
echo.
echo Step 1: Registering 8:45 AM pre-market scan task...
schtasks /create /tn "DalalStreet_PreMarket_845AM" /tr "\"C:\Program Files\Python312\python.exe\" \"E:\SELFLEARNINGAGENT\TradingAgents\run_daily_premarket_scheduler.py\" --now --launch-dashboard" /sc weekly /d MON,TUE,WED,THU,FRI /st 08:45 /f
echo.
if %errorlevel% equ 0 (
    echo [SUCCESS] Task registered: DalalStreet_PreMarket_845AM
    echo           Fires at 08:45 AM every Mon-Fri
    echo           Runs scan + auto-opens dashboard in browser
) else (
    echo [FAILED] Run this file as Administrator and try again.
)
echo.
echo Step 2: Verifying task...
schtasks /query /tn "DalalStreet_PreMarket_845AM" /fo list
echo.
pause
