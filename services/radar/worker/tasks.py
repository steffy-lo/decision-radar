import sys
import time
from services.radar.config import settings


def run_worker():
    """Worker entrypoint process for background ingestion and assessment jobs."""
    print(f"[*] Starting Decision Radar Background Worker...", flush=True)
    print(f"[*] Environment: {settings.ENVIRONMENT}", flush=True)
    print(f"[*] Firebase Project: {settings.FIREBASE_PROJECT_ID}", flush=True)
    if settings.FIRESTORE_EMULATOR_HOST:
        print(f"[*] Firestore Emulator Target: {settings.FIRESTORE_EMULATOR_HOST}", flush=True)
    print(f"[+] Worker ready and listening for task triggers.", flush=True)
    
    # In continuous execution mode, worker waits for queued events
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n[-] Worker shutting down gracefully.")
        sys.exit(0)


if __name__ == "__main__":
    run_worker()
