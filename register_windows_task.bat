@echo off
echo ======================================================================
echo   REGISTERING DALAL STREET 8:45 AM PRE-MARKET SCAN (WINDOWS TASK SCHEDULER)
echo ======================================================================
echo.
schtasks /create /tn "NSE_Premarket_Scan_845AM" /tr "python E:\SELFLEARNINGAGENT\TradingAgents\run_daily_premarket_scheduler.py --now" /sc weekly /d MON,TUE,WED,THU,FRI /st 08:45 /f
echo.
if %errorlevel% equ 0 (
    echo [SUCCESS] Windows Task 'NSE_Premarket_Scan_845AM' registered for 08:45 AM Mon-Fri!
) else (
    echo [NOTE] If permission denied, please run cmd as Administrator.
)
echo.
pause
