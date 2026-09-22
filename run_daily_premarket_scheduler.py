#!/usr/bin/env python3
"""Daily Automated Pre-Market Scheduler for NSE Trading Engine.

Schedules the pre-market top gainer scan at 8:45 AM IST every weekday,
saves session state so the dashboard picks it up automatically, and
optionally auto-launches the Streamlit dashboard + opens your browser.

Usage:
    python run_daily_premarket_scheduler.py                    # Persistent 8:45 AM trigger
    python run_daily_premarket_scheduler.py --now              # Run scan immediately (test)
    python run_daily_premarket_scheduler.py --launch-dashboard # Also auto-open browser
"""

import argparse
import datetime
import os
import sys
import time
import subprocess
import socket
import webbrowser

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

PYTHON = sys.executable
DASHBOARD_SCRIPT = os.path.join(PROJECT_ROOT, "dashboard.py")
SCAN_SCRIPT = os.path.join(PROJECT_ROOT, "scan_premarket_top_gainers.py")
LOG_DIR = os.path.join(PROJECT_ROOT, "results", "scheduler_logs")

NSE_HOLIDAYS_2026 = {
    datetime.date(2026, 1, 26),
    datetime.date(2026, 3, 27),
    datetime.date(2026, 4, 3),
    datetime.date(2026, 4, 14),
    datetime.date(2026, 5, 1),
    datetime.date(2026, 8, 15),
    datetime.date(2026, 10, 2),
    datetime.date(2026, 10, 20),
    datetime.date(2026, 11, 8),
    datetime.date(2026, 12, 25),
}


def is_nse_trading_day(dt):
    return dt.weekday() < 5 and dt not in NSE_HOLIDAYS_2026


def execute_premarket_scan(bypass_regime=True, capital=100000.0, risk=2.0):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n[{}] TRIGGER: Executing 8:45 AM Pre-Market Scan...".format(now_str))

    os.makedirs(LOG_DIR, exist_ok=True)
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(LOG_DIR, "premarket_scan_{}.log".format(today_str))

    cmd = [PYTHON, SCAN_SCRIPT, "--top-n", "3", "--capital", str(capital), "--risk", str(risk)]
    if bypass_regime:
        cmd.append("--bypass-regime")

    success = False
    try:
        with open(log_file, "a", encoding="utf-8") as flog:
            flog.write("\n{}\n[EXECUTION LOG: {}]\n{}\n".format("="*70, now_str, "="*70))
            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", cwd=PROJECT_ROOT
            )
            flog.write(result.stdout)
            print(result.stdout)
            success = result.returncode == 0
        status = "OK" if success else "FAILED (code {})".format(result.returncode)
        print("[{}] Scan {}. Log: {}".format(now_str, status, log_file))
    except Exception as exc:
        print("[{}] ERROR: {}".format(now_str, exc))
    return success


def is_dashboard_running(port=8501):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", port)) == 0
    except Exception:
        return False


def launch_dashboard(port=8501):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if is_dashboard_running(port):
        print("[{}] Dashboard already running on port {} - skipping relaunch.".format(now_str, port))
    else:
        cmd = [PYTHON, "-m", "streamlit", "run", DASHBOARD_SCRIPT,
               "--server.headless", "true", "--server.port", str(port)]
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        subprocess.Popen(cmd, cwd=PROJECT_ROOT, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, creationflags=flags)
        time.sleep(4)
        print("[{}] Dashboard launched -> http://localhost:{}".format(now_str, port))
    webbrowser.open("http://localhost:{}".format(port))


def run_scheduler_loop(target_time="08:45", launch_dash=False, capital=100000.0, risk=2.0):
    target_hour, target_minute = map(int, target_time.split(":"))
    print("=" * 65)
    print("  DALAL STREET 8:45 AM PRE-MARKET AUTO-SCHEDULER")
    print("  Schedule : {} AM IST | Mon-Fri | Excl. NSE Holidays".format(target_time))
    print("  Capital  : Rs{:,.0f} | Risk: {}% per trade".format(capital, risk))
    print("=" * 65)
    print("[*] Scheduler active. Waiting for {} AM trigger...".format(target_time))
    print("    Press Ctrl+C to stop.\n")

    last_run_date = None
    while True:
        now = datetime.datetime.now()
        today = now.date()
        at_trigger = now.hour == target_hour and now.minute == target_minute
        if at_trigger and last_run_date != today:
            if is_nse_trading_day(today):
                success = execute_premarket_scan(bypass_regime=True, capital=capital, risk=risk)
                last_run_date = today
                if success and launch_dash:
                    launch_dashboard()
            else:
                print("[{}] Weekend / Holiday — scan skipped.".format(now.strftime("%Y-%m-%d %H:%M")))
                last_run_date = today
        time.sleep(30)


def main():
    parser = argparse.ArgumentParser(description="Automated 8:45 AM NSE Pre-Market Scanner")
    parser.add_argument("--now", action="store_true", help="Run scan immediately and exit")
    parser.add_argument("--time", type=str, default="08:45", help="Target HH:MM (default: 08:45)")
    parser.add_argument("--capital", type=float, default=100000.0, help="Capital in INR")
    parser.add_argument("--risk", type=float, default=2.0, help="Risk per trade %%")
    parser.add_argument("--launch-dashboard", action="store_true", help="Auto-open dashboard after scan")
    args = parser.parse_args()

    if args.now:
        print("[*] Running immediate scan...")
        execute_premarket_scan(bypass_regime=True, capital=args.capital, risk=args.risk)
        if args.launch_dashboard:
            launch_dashboard()
    else:
        run_scheduler_loop(target_time=args.time, launch_dash=args.launch_dashboard,
                           capital=args.capital, risk=args.risk)


if __name__ == "__main__":
    main()
