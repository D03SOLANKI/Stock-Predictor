#!/usr/bin/env python3
"""Launch script for the Dalal Street Trading Intelligence Dashboard."""

import os
import subprocess
import sys


def main():
    dashboard_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.py")
    print(f"[*] Launching Streamlit Trading Dashboard from {dashboard_path}...")
    cmd = [sys.executable, "-m", "streamlit", "run", dashboard_path, "--server.headless", "false"]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n[+] Dashboard stopped by user.")


if __name__ == "__main__":
    main()
