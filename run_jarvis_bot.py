from jarvis import JARVIS

jarvis = JARVIS()
jarvis.boot()

print("JARVIS running with Telegram bot enabled.")
print("Send commands via Telegram...")

# Keep running
try:
    while jarvis._running:
        import time
        time.sleep(1)
except KeyboardInterrupt:
    print("\nShutting down...")
    jarvis.telegram.stop() if jarvis.telegram else None