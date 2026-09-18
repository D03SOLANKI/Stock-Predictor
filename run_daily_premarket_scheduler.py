#!/usr/bin/env python3
"""Daily Automated Pre-Market Scheduler for NSE Trading Engine.

Schedules and executes the pre-market top gainer scan automatically at 8:45 AM IST
on every NSE trading weekday (Monday - Friday).

Usage:
    python run_daily_premarket_scheduler.py
    python run_daily_premarket_scheduler.py --now   # Run immediately for testing
"""

import argparse
import datetime
import os
import sys
import time
import subprocess

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def is_nse_trading_day(dt: datetime.date) -> bool:
    """Check if given date is a weekday (Mon-Fri)."""
    # Monday = 0, Sunday = 6
    if dt.weekday() >= 5:
        return False
    
    # 2026 NSE Key Trading Holidays (Sample list)
    nse_holidays_2026 = {
        datetime.date(2026, 1, 26),  # Republic Day
        datetime.date(2026, 3, 27),  # Holi
        datetime.date(2026, 4, 3),   # Good Friday
        datetime.date(2026, 4, 14),  # Ambedkar Jayanti
        datetime.date(2026, 5, 1),   # Maharashtra Day
        datetime.date(2026, 8, 15),  # Independence Day
        datetime.date(2026, 10, 2),  # Gandhi Jayanti
        datetime.date(2026, 10, 20), # Dussehra
        datetime.date(2026, 11, 8),  # Diwali Laxmi Pujan
        datetime.date(2026, 12, 25), # Christmas
    }
    if dt in nse_holidays_2026:
        return False
        
    return True


def execute_premarket_scan():
    """Trigger pre-market scan script and log output."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{now_str}] 🚀 TRADING ENGINE TRIGGERED: Executing 8:45 AM Pre-Market Scan...")
    
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "scheduler_logs")
    os.makedirs(log_dir, exist_ok=True)
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(log_dir, f"premarket_scan_{today_str}.log")

    cmd = [
        sys.executable,
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "scan_premarket_top_gainers.py"),
        "--top-n", "3",
        "--capital", "100000",
        "--risk", "2.0",
        "--bypass-regime"
    ]

    try:
        with open(log_file, "a", encoding="utf-8") as f_log:
            f_log.write(f"\n{'='*70}\n[EXECUTION LOG: {now_str}]\n{'='*70}\n")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True)
            f_log.write(result.stdout)
            print(result.stdout)
        print(f"[{now_str}] ✅ Scan completed successfully. Log saved to: {log_file}")
    except subprocess.CalledProcessError as exc:
        print(f"[{now_str}] ❌ Error running scan: {exc.output}")
    except Exception as exc:
        print(f"[{now_str}] ❌ Unexpected error: {exc}")


def run_scheduler_loop(target_time_str: str = "08:45"):
    """Run persistent loop waiting for 8:45 AM on trading days."""
    target_hour, target_minute = map(int, target_time_str.split(":"))
    print("=" * 75)
    print(f"  DALAL STREET AUTOMATED 8:45 AM PRE-MARKET SCHEDULER")
    print(f"  Target Schedule: {target_time_str} AM IST (Mon - Fri, Excl. NSE Holidays)")
    print("=" * 75 + "\n")
    print("[*] Scheduler active and waiting for 8:45 AM market trigger...")

    last_run_date = None

    while True:
        now = datetime.datetime.now()
        today = now.date()

        # Check if today is a trading day
        if is_nse_trading_day(today):
            # If current time is 8:45 AM and we haven't run today yet
            if now.hour == target_hour and now.minute == target_minute and last_run_date != today:
                execute_premarket_scan()
                last_run_date = today

        # Sleep for 30 seconds before next check
        time.sleep(30)


def main():
    parser = argparse.ArgumentParser(description="Automated 8:45 AM Pre-Market Scheduler")
    parser.add_argument("--now", action="store_true", help="Run pre-market scan immediately and exit")
    parser.add_argument("--time", type=str, default="08:45", help="Target time in HH:MM format (default: 08:45)")
    args = parser.parse_args()

    if args.now:
        print("[*] Executing immediate test scan...")
        execute_premarket_scan()
    else:
        run_scheduler_loop(target_time_str=args.time)


if __name__ == "__main__":
    main()
