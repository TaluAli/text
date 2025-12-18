import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"


def main():
    procs = []
    backend_cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"]
    frontend_cmd = ["npm", "run", "dev"]

    try:
        procs.append(
            subprocess.Popen(
                backend_cmd,
                cwd=BACKEND_DIR,
            )
        )
        procs.append(
            subprocess.Popen(
                frontend_cmd,
                cwd=FRONTEND_DIR,
            )
        )
        print("Backend and frontend started. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping processes...")
    finally:
        for p in procs:
            if p and p.poll() is None:
                p.send_signal(signal.SIGTERM)
        for p in procs:
            if p:
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()


if __name__ == "__main__":
    main()
