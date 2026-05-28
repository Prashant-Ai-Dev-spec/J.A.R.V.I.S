"""
Personal Telegram secretary for J.A.R.V.I.S.

This listens to the owner's Telegram account through Telegram's client API
(Telethon), not the Bot API. It can therefore react to incoming personal DMs
after the owner completes a one-time login.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "jarvis_config.json"
DEFAULT_SESSION = BASE_DIR / ".jarvis_runtime" / "telegram_personal"
LOCK_FILE = BASE_DIR / ".jarvis_runtime" / "telegram_personal.lock"
FALLBACK_REPLY = (
    "Hi, main JARVIS bol raha hoon. Prashant abhi available nahi hain, "
    "maine aapka message note kar liya hai. Agar urgent hai to please details "
    "bhej dijiye, main unhe inform kar dunga."
)


class PersonalTelegramSecretary:
    def __init__(
        self,
        jarvis_instance: Any = None,
        *,
        config_path: str | Path = CONFIG_FILE,
    ) -> None:
        self.jarvis = jarvis_instance
        self.config_path = Path(config_path)
        self.cfg = self._load_config()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._last_reply: dict[int, float] = {}
        self._lock_path = LOCK_FILE

    def start_background(self) -> threading.Thread | None:
        if not self.enabled:
            return None
        if self._thread and self._thread.is_alive():
            return self._thread
        self._stop.clear()
        self._thread = threading.Thread(target=self._thread_main, name="JarvisPersonalTelegram", daemon=True)
        self._thread.start()
        return self._thread

    def stop(self) -> None:
        self._stop.set()

    @property
    def enabled(self) -> bool:
        return bool(self.cfg.get("telegram_personal_enabled", False))

    def _load_config(self) -> dict[str, Any]:
        try:
            if self.config_path.exists():
                return json.loads(self.config_path.read_text(encoding="utf-8-sig"))
        except Exception:
            logging.exception("Could not read personal Telegram config")
        return {}

    def _settings(self) -> tuple[int, str, str]:
        api_id = self.cfg.get("telegram_api_id")
        api_hash = str(self.cfg.get("telegram_api_hash") or "").strip()
        session = str(self.cfg.get("telegram_personal_session") or DEFAULT_SESSION).strip()
        if not api_id or not api_hash:
            raise ValueError("Set telegram_api_id and telegram_api_hash in jarvis_config.json")
        return int(api_id), api_hash, session

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run())
        except Exception:
            logging.exception("Personal Telegram secretary stopped")

    async def _run(self) -> None:
        try:
            from telethon import TelegramClient, events
        except Exception as exc:
            raise RuntimeError("Telethon missing. Install with: pip install telethon") from exc

        if not self._acquire_process_lock():
            logging.error("Personal Telegram secretary is already running. Stop the other copy before starting again.")
            return

        api_id, api_hash, session = self._settings()
        client = TelegramClient(session, api_id, api_hash)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                logging.error(
                    "Personal Telegram session is not logged in. Run: python jarvis_personal_telegram.py --login"
                )
                return

            @client.on(events.NewMessage(incoming=True))
            async def on_new_message(event):  # noqa: ANN001
                await self._handle_new_message(client, event)

            logging.info("Personal Telegram secretary listening for incoming DMs")
            while not self._stop.is_set():
                await asyncio.sleep(0.5)
        finally:
            await client.disconnect()
            self._release_process_lock()

    def _acquire_process_lock(self) -> bool:
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(str(self._lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if self._lock_is_stale():
                try:
                    self._lock_path.unlink()
                except OSError:
                    return False
                return self._acquire_process_lock()
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        return True

    def _lock_is_stale(self) -> bool:
        try:
            pid = int(self._lock_path.read_text(encoding="utf-8").strip())
        except Exception:
            return True
        if pid == os.getpid():
            return True
        if os.name == "nt":
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                return str(pid) not in (result.stdout or "")
            except Exception:
                return False
        try:
            os.kill(pid, 0)
            return False
        except OSError:
            return True

    def _release_process_lock(self) -> None:
        try:
            if self._lock_path.exists():
                pid = self._lock_path.read_text(encoding="utf-8").strip()
                if pid == str(os.getpid()):
                    self._lock_path.unlink()
        except Exception:
            logging.exception("Could not release personal Telegram lock")

    async def _handle_new_message(self, client: Any, event: Any) -> None:
        if bool(self.cfg.get("telegram_personal_dm_only", True)) and not event.is_private:
            return
        if getattr(event.message, "out", False):
            return

        chat_id = int(event.chat_id or 0)
        text = str(getattr(event.message, "message", "") or "").strip()
        if not text:
            return
        sender = await event.get_sender()
        sender_name = self._sender_name(sender)
        if self._should_ignore_sender(sender):
            logging.info("Skipping Telegram auto-reply to ignored sender %s (%s)", sender_name, chat_id)
            return
        if self._recently_replied(chat_id):
            logging.info("Skipping Telegram auto-reply to %s due to cooldown", chat_id)
            return

        logging.info("Personal Telegram DM from %s (%s): %s", sender_name, chat_id, text[:160])

        reply = await asyncio.to_thread(self._make_reply, sender_name, text)
        await event.respond(reply[:3900])
        self._last_reply[chat_id] = time.time()
        await self._notify_owner(client, sender_name, text, reply)
        logging.info("Personal Telegram auto-reply sent to %s", sender_name)

    async def _notify_owner(self, client: Any, sender_name: str, incoming: str, reply: str) -> None:
        if not bool(self.cfg.get("telegram_personal_notify_owner", True)):
            return
        incoming_preview = incoming[:500]
        reply_preview = reply[:700]
        note = (
            "JARVIS auto-replied on Telegram\n"
            f"From: {sender_name}\n"
            f"Incoming: {incoming_preview}\n"
            f"Reply: {reply_preview}"
        )
        try:
            await client.send_message("me", note[:3900])
        except Exception:
            logging.exception("Could not send Telegram owner notification")

    def _recently_replied(self, chat_id: int) -> bool:
        cooldown = int(self.cfg.get("telegram_personal_reply_cooldown_sec", 1800) or 0)
        if cooldown <= 0:
            return False
        last = self._last_reply.get(chat_id, 0)
        return (time.time() - last) < cooldown

    def _should_ignore_sender(self, sender: Any) -> bool:
        if bool(getattr(sender, "bot", False)):
            return True
        sender_id = str(getattr(sender, "id", "") or "").strip()
        bot_token = str(self.cfg.get("telegram_bot_token", "") or "").strip()
        bot_id = bot_token.split(":", 1)[0] if ":" in bot_token else ""
        if sender_id and bot_id and sender_id == bot_id:
            return True
        ignore_raw = self.cfg.get("telegram_personal_ignore_senders", [])
        if isinstance(ignore_raw, str):
            ignore_raw = [item.strip() for item in ignore_raw.split(",")]
        ignore = {str(item).strip().lower().lstrip("@") for item in ignore_raw if str(item).strip()}
        ignore.update({"myjarvisbot", "jodjarvisbot", "jarvisbot"})
        values = {
            sender_id.lower(),
            str(getattr(sender, "username", "") or "").lower().lstrip("@"),
            self._sender_name(sender).lower().lstrip("@"),
        }
        compact_values = {re.sub(r"[^a-z0-9]+", "", value) for value in values if value}
        if ignore & values or ignore & compact_values:
            return True
        return any("jarvisbot" in value or "jodjarvis" in value for value in compact_values)

    def _make_reply(self, sender_name: str, incoming: str) -> str:
        if not bool(self.cfg.get("telegram_personal_ai_auto_reply", False)):
            return FALLBACK_REPLY
        prompt = (
            "You are JARVIS, Prashant's personal secretary. "
            "Reply to this Telegram message on Prashant's behalf only as a secretary, "
            "not pretending to be Prashant. Keep it short, warm Hinglish, 2-3 sentences. "
            "Say Prashant is currently unavailable, the message is noted, and ask for urgent details if needed.\n\n"
            f"Sender: {sender_name}\nMessage: {incoming}"
        )
        ai = getattr(self.jarvis, "ai", None)
        chat = getattr(ai, "chat", None)
        if callable(chat):
            try:
                reply = str(chat(prompt, context="Telegram personal auto-reply") or "").strip()
                return reply or FALLBACK_REPLY
            except Exception:
                logging.exception("JARVIS AI reply failed for personal Telegram")
        return FALLBACK_REPLY

    @staticmethod
    def _sender_name(sender: Any) -> str:
        first = str(getattr(sender, "first_name", "") or "").strip()
        last = str(getattr(sender, "last_name", "") or "").strip()
        username = str(getattr(sender, "username", "") or "").strip()
        parts = [" ".join(p for p in [first, last] if p).strip()]
        if username:
            parts.append(f"@{username}")
        return " ".join(p for p in parts if p) or str(getattr(sender, "id", "Unknown"))


_default_secretary: PersonalTelegramSecretary | None = None


def start_background(jarvis_instance: Any = None, config_path: str | Path = CONFIG_FILE) -> threading.Thread | None:
    global _default_secretary
    if _default_secretary and _default_secretary._thread and _default_secretary._thread.is_alive():
        return _default_secretary._thread
    _default_secretary = PersonalTelegramSecretary(jarvis_instance=jarvis_instance, config_path=config_path)
    return _default_secretary.start_background()


def stop_background() -> None:
    if _default_secretary:
        _default_secretary.stop()


async def login(config_path: str | Path = CONFIG_FILE) -> None:
    try:
        from telethon import TelegramClient
    except Exception as exc:
        raise RuntimeError("Telethon missing. Install with: pip install telethon") from exc

    secretary = PersonalTelegramSecretary(config_path=config_path)
    api_id, api_hash, session = secretary._settings()
    client = TelegramClient(session, api_id, api_hash)
    await client.start()
    me = await client.get_me()
    print(f"Logged in as {secretary._sender_name(me)}")
    await client.disconnect()


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--login", action="store_true", help="One-time login for the personal Telegram account")
    args = parser.parse_args()
    if args.login:
        asyncio.run(login())
    else:
        start_background()
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            stop_background()
