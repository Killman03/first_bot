"""Open copied Zoom meeting links on Windows.

The program watches the Windows clipboard and opens a newly copied, valid Zoom
meeting URL with the application's default handler.  It uses only Python's
standard library.
"""

from __future__ import annotations

import ctypes
import os
import re
import sys
import time
from datetime import datetime
from tkinter import TclError, Tk
from urllib.parse import urlsplit


POLL_INTERVAL_MS = 100
REOPEN_COOLDOWN_SECONDS = 15
ALLOWED_HOSTS = ("zoom.us", "zoom.com")

# A copied Telegram message can contain text around the URL. Whitespace and
# characters that cannot occur unescaped in a URL terminate the match.
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
MEETING_PATH_PATTERN = re.compile(
    r"^/(?:j/(?P<direct>\d{9,13})|wc/(?P<web>\d{9,13})/join)(?:/|$)",
    re.IGNORECASE,
)
TRAILING_PUNCTUATION = ".,;:!?)]}>\u00bb\u201d\u2019"


def log(message: str) -> None:
    """Write a timestamped status message and flush it immediately."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def is_official_zoom_host(hostname: str | None) -> bool:
    """Return True only for zoom.us/zoom.com and their real subdomains."""
    if not hostname:
        return False

    hostname = hostname.rstrip(".").lower()
    return any(
        hostname == allowed or hostname.endswith(f".{allowed}")
        for allowed in ALLOWED_HOSTS
    )


def normalize_zoom_meeting_url(candidate: str) -> str | None:
    """Validate a candidate and return a normalized Zoom meeting URL."""
    candidate = candidate.rstrip(TRAILING_PUNCTUATION)

    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError:
        return None

    if parsed.scheme.lower() not in {"http", "https"}:
        return None
    if not is_official_zoom_host(parsed.hostname):
        return None
    if parsed.username or parsed.password:
        return None
    if port not in (None, 80, 443):
        return None
    if not MEETING_PATH_PATTERN.match(parsed.path):
        return None

    # Force HTTPS while preserving the host, meeting ID and encrypted password.
    return parsed._replace(scheme="https").geturl()


def extract_zoom_meeting_urls(text: str) -> list[str]:
    """Extract unique, valid Zoom meeting URLs from arbitrary clipboard text."""
    urls: list[str] = []
    for match in URL_PATTERN.finditer(text):
        normalized = normalize_zoom_meeting_url(match.group(0))
        if normalized and normalized not in urls:
            urls.append(normalized)
    return urls


def clipboard_sequence_number() -> int:
    """Return the Windows clipboard revision number."""
    return int(ctypes.windll.user32.GetClipboardSequenceNumber())


def open_url(url: str) -> None:
    """Open a URL with its Windows default handler."""
    os.startfile(url)  # type: ignore[attr-defined]


class ZoomClipboardWatcher:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.withdraw()
        self.last_sequence = clipboard_sequence_number()
        self.opened_at: dict[str, float] = {}

    def read_clipboard_text(self) -> str | None:
        try:
            value = self.root.clipboard_get()
        except TclError:
            return None
        return value if isinstance(value, str) else None

    def poll(self) -> None:
        sequence = clipboard_sequence_number()
        if sequence != self.last_sequence:
            self.last_sequence = sequence
            text = self.read_clipboard_text()
            if text:
                self.handle_text(text)

        self.root.after(POLL_INTERVAL_MS, self.poll)

    def handle_text(self, text: str) -> None:
        urls = extract_zoom_meeting_urls(text)
        if not urls:
            return

        now = time.monotonic()
        # Open the first meeting link only. This avoids launching several Zoom
        # windows when a copied message happens to contain multiple old links.
        url = urls[0]
        previous_open = self.opened_at.get(url)
        if previous_open is not None and now - previous_open < REOPEN_COOLDOWN_SECONDS:
            log("Повторная ссылка проигнорирована (защита от двойного запуска).")
            return

        try:
            open_url(url)
        except OSError as error:
            log(f"Не удалось открыть ссылку: {error}")
            return

        self.opened_at[url] = now
        meeting_match = MEETING_PATH_PATTERN.match(urlsplit(url).path)
        meeting_label = "неизвестен"
        if meeting_match:
            meeting_label = meeting_match.group("direct") or meeting_match.group("web")
        log(f"Zoom-ссылка открыта (Meeting ID: {meeting_label}).")

        try:
            import winsound

            winsound.MessageBeep(winsound.MB_OK)
        except (ImportError, RuntimeError):
            pass

    def run(self) -> None:
        log("Наблюдение за буфером запущено.")
        log("Скопируйте Zoom-ссылку. Для остановки нажмите Ctrl+C.")
        self.root.after(POLL_INTERVAL_MS, self.poll)
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.root.destroy()


def main() -> int:
    if sys.platform != "win32":
        print("Эта программа предназначена для Windows.", file=sys.stderr)
        return 1

    try:
        ZoomClipboardWatcher().run()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
