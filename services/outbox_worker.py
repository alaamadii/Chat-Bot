import os
import time

from db.database import init_db
from services.outbox import outbox


def run() -> None:
    init_db()
    interval = max(1.0, float(os.getenv("OUTBOX_POLL_SECONDS", "2")))
    while True:
        outbox.process_pending(limit=int(os.getenv("OUTBOX_BATCH_SIZE", "50")))
        time.sleep(interval)


if __name__ == "__main__":
    run()
