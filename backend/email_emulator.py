import json
from datetime import datetime
from pathlib import Path


LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "email_emulator.log"


def send_email_notification(email: str, title: str, remind_at: datetime) -> None:
    """Persist and print an email delivery record instead of contacting SMTP."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "sent_at": datetime.now().astimezone().isoformat(),
        "email": email,
        "title": title,
        "remind_at": remind_at.isoformat(),
    }
    line = json.dumps(record, ensure_ascii=False)
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{line}\n")
    print(f"[email-emulator] {line}", flush=True)
