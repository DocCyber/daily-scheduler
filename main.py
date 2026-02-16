#!/usr/bin/env python3
"""
Daily Scheduler - Task management with time blocks

Usage:
    python main.py
"""

import sys
from src.ui.main_window import MainWindow

def main():
    """Main entry point for the Daily Scheduler application"""
    try:
        app = MainWindow()
        app.mainloop()
    except Exception as e:
        print(f"Error starting application: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
