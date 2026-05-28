"""
Telegram secretary bot for J.A.R.V.I.S.

This module is safe to import from jarvis.py. Call start_background() to run the
bot in a daemon thread.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "jarvis_config.json"
MODEL_NAME = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = (
    "You are JARVIS, Prashant's personal AI secretary. "
    "Prashant is currently unavailable, but you are not just an answering machine. "
    "Reply politely in Hinglish, keep it short, professional, warm, and helpful. "
    "Do not pretend to be Prashant. Always include these ideas naturally: "
    "1) the message has been forwarded to Prashant, "
    "2) ask if it is urgent, "
    "3) ask how you can help or ask them to leave details, "
    "4) say you will inform Prashant when he is available. "
    "Avoid dry one-line replies."
)

OWNER_SYSTEM_PROMPT = (
    "You are JARVIS, Prashant's personal AI assistant. "
    "Talk directly to Prashant in warm Hinglish. Be concise, useful, and clear. "
    "Do not say this is secretary mode. If a task needs local computer access, "
    "say that the main JARVIS desktop process should handle it."
)

FALLBACK_REPLY = (
    "Namaste, main JARVIS bol raha hoon. Prashant abhi unavailable hain, "
    "lekin aapka message un tak forward kar diya gaya hai. Agar urgent hai ya "
    "aapko kisi cheez mein madad chahiye, mujhe details bata dijiye; Prashant "
    "available hote hi main unhe inform kar dunga."
)

_thread: threading.Thread | None = None
_stop_event = threading.Event()
_state_lock = threading.Lock()
_auto_reply_enabled = True


def _load_config(path: str | Path = CONFIG_FILE) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        logging.exception("Could not read JARVIS Telegram config")
        return {}


def _read_settings(config_path: str | Path = CONFIG_FILE) -> tuple[str, str, int]:
    cfg = _load_config(config_path)
    bot_token = str(cfg.get("BOT_TOKEN") or cfg.get("telegram_bot_token") or "").strip()
    groq_key = str(cfg.get("GROQ_KEY") or cfg.get("groq_api_key") or "").strip()
    owner_raw = cfg.get("YOUR_TELEGRAM_ID", cfg.get("telegram_allowed_user_id"))

    try:
        owner_id = int(owner_raw)
    except Exception as exc:
        raise ValueError("YOUR_TELEGRAM_ID or telegram_allowed_user_id must be set in jarvis_config.json") from exc

    missing = []
    if not bot_token:
        missing.append("BOT_TOKEN or telegram_bot_token")
    if not groq_key:
        missing.append("GROQ_KEY or groq_api_key")
    if missing:
        raise ValueError("Missing config in jarvis_config.json: " + ", ".join(missing))

    return bot_token, groq_key, owner_id


def _non_owner_ai_reply_enabled(config_path: str | Path = CONFIG_FILE) -> bool:
    cfg = _load_config(config_path)
    return bool(cfg.get("telegram_secretary_ai_auto_reply", False))


def is_auto_reply_enabled() -> bool:
    with _state_lock:
        return _auto_reply_enabled


def set_auto_reply_enabled(enabled: bool) -> None:
    global _auto_reply_enabled
    with _state_lock:
        _auto_reply_enabled = bool(enabled)


def _sender_label(message) -> str:
    user = message.from_user
    if not user:
        return "Unknown sender"
    name = " ".join(part for part in [user.first_name, user.last_name] if part).strip()
    handle = f"@{user.username}" if user.username else ""
    return " ".join(part for part in [name or str(user.id), handle, f"(id: {user.id})"] if part)


def _message_text(message) -> str:
    return (getattr(message, "text", None) or getattr(message, "caption", None) or "").strip()


def _chat_label(message) -> str:
    chat = getattr(message, "chat", None)
    if not chat:
        return f"chat_id={getattr(message, 'chat_id', 'unknown')}"
    title = getattr(chat, "title", None) or getattr(chat, "full_name", None) or getattr(chat, "username", None)
    return f"{title or getattr(chat, 'id', 'unknown')} ({getattr(chat, 'type', 'unknown')}, id: {getattr(chat, 'id', 'unknown')})"


async def _safe_reply_text(message, text: str) -> bool:
    try:
        await message.reply_text(text[:3900])
        return True
    except Exception:
        logging.exception("Telegram reply_text failed; trying direct send_message")
    try:
        await message.get_bot().send_message(chat_id=message.chat_id, text=text[:3900])
        return True
    except Exception:
        logging.exception("Telegram direct send_message failed")
        return False


def _make_groq_reply(groq_key: str, sender: str, message_text: str) -> str:
    try:
        from groq import Groq
    except Exception as exc:
        logging.exception("Groq library is not available")
        return FALLBACK_REPLY

    client = Groq(api_key=groq_key)
    user_prompt = (
        f"Sender: {sender}\n"
        f"Message: {message_text or '[non-text message]'}\n\n"
        "Write a short Hinglish secretary reply in 2-3 sentences. "
        "Do not only say Prashant is unavailable; offer help and ask if it is urgent."
    )
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.45,
        max_tokens=180,
    )
    reply = (response.choices[0].message.content or "").strip()
    return reply or FALLBACK_REPLY


def _make_owner_reply(groq_key: str, message_text: str) -> str:
    try:
        from groq import Groq
    except Exception:
        logging.exception("Groq library is not available")
        return "Bhai main online hoon. Batao kya karna hai?"

    client = Groq(api_key=groq_key)
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": OWNER_SYSTEM_PROMPT},
            {"role": "user", "content": message_text or "Hi"},
        ],
        temperature=0.45,
        max_tokens=300,
    )
    reply = (response.choices[0].message.content or "").strip()
    return reply or "Bhai main online hoon. Batao kya karna hai?"


async def _forward_to_owner(context, owner_id: int, message) -> None:
    sender = _sender_label(message)
    text = _message_text(message)
    preview = text[:700] if text else "[media/non-text message]"
    try:
        await context.bot.send_message(
            chat_id=owner_id,
            text=f"JARVIS notification\nFrom: {sender}\nChat: {_chat_label(message)}\nMessage: {preview}",
        )
    except Exception:
        logging.exception("Could not notify Telegram owner")
    try:
        await context.bot.copy_message(
            chat_id=owner_id,
            from_chat_id=message.chat_id,
            message_id=message.message_id,
        )
    except Exception:
        logging.exception("Could not copy Telegram message to owner")


async def _handle_online(update, context) -> None:
    _, _, owner_id = context.application.bot_data["jarvis_settings"]
    if not update.effective_user or update.effective_user.id != owner_id:
        return
    set_auto_reply_enabled(False)
    await update.message.reply_text("JARVIS secretary auto-reply silent hai. Messages sirf forward honge.")


async def _handle_offline(update, context) -> None:
    _, _, owner_id = context.application.bot_data["jarvis_settings"]
    if not update.effective_user or update.effective_user.id != owner_id:
        return
    set_auto_reply_enabled(True)
    await update.message.reply_text("JARVIS secretary auto-reply resume ho gaya.")


async def _handle_status(update, context) -> None:
    _, _, owner_id = context.application.bot_data["jarvis_settings"]
    if not update.effective_user or update.effective_user.id != owner_id:
        return
    mode = "AUTO-REPLY ON" if is_auto_reply_enabled() else "SILENT FORWARD-ONLY"
    await update.message.reply_text(
        f"JARVIS secretary status: {mode}.\n"
        "Note: Prashant ke own messages par secretary auto-reply nahi karta. "
        "Test ke liye kisi doosre Telegram account/device se message bhejo."
    )


async def _handle_start(update, context) -> None:
    _, _, owner_id = context.application.bot_data["jarvis_settings"]
    if not update.message:
        return
    sender_id = update.effective_user.id if update.effective_user else None
    if sender_id == owner_id:
        await _safe_reply_text(
            update.message,
            "JARVIS online hai bhai. Message bhejo, main reply karunga. Secretary controls: /status, /offline, /online.",
        )
        return
    await _safe_reply_text(update.message, FALLBACK_REPLY)


async def _handle_ping(update, context) -> None:
    _, _, owner_id = context.application.bot_data["jarvis_settings"]
    if update.message and update.effective_user and update.effective_user.id == owner_id:
        await _safe_reply_text(update.message, "JARVIS secretary reachable hai.")


async def _handle_message(update, context) -> None:
    if not update.message:
        return

    bot_token, groq_key, owner_id = context.application.bot_data["jarvis_settings"]
    message = update.message
    sender_id = update.effective_user.id if update.effective_user else None
    logging.info(
        "Incoming Telegram update from %s in %s: %s",
        _sender_label(message),
        _chat_label(message),
        _message_text(message)[:120] or "[media/non-text message]",
    )

    if sender_id == owner_id:
        text = _message_text(message)
        try:
            reply = await asyncio.to_thread(_make_owner_reply, groq_key, text)
        except Exception:
            logging.exception("Owner Telegram reply failed")
            reply = "Bhai main online hoon, par abhi reply generate nahi ho paya."
        await _safe_reply_text(message, reply)
        return

    logging.info("Secretary message from %s: %s", _sender_label(message), _message_text(message)[:120])
    await _forward_to_owner(context, owner_id, message)

    if not is_auto_reply_enabled():
        logging.info("Auto-reply is off; forwarded only.")
        return

    sender = _sender_label(message)
    text = _message_text(message)
    config_path = context.application.bot_data.get("jarvis_config_path", CONFIG_FILE)
    if _non_owner_ai_reply_enabled(config_path):
        try:
            reply = await asyncio.to_thread(_make_groq_reply, groq_key, sender, text)
        except Exception:
            logging.exception("Groq reply failed")
            reply = FALLBACK_REPLY
    else:
        reply = FALLBACK_REPLY
    sent = await _safe_reply_text(message, reply)
    if sent:
        logging.info("Secretary auto-reply sent to %s", sender)
    else:
        logging.error("Secretary auto-reply could not be delivered to %s", sender)


async def _run_bot(config_path: str | Path = CONFIG_FILE) -> None:
    try:
        from telegram.ext import Application, CommandHandler, MessageHandler, filters
    except Exception as exc:
        raise RuntimeError("python-telegram-bot is required. Install with: pip install python-telegram-bot") from exc

    settings = _read_settings(config_path)
    bot_token, _, _ = settings

    application = Application.builder().token(bot_token).build()
    application.bot_data["jarvis_settings"] = settings
    application.bot_data["jarvis_config_path"] = str(config_path)
    application.add_handler(CommandHandler("start", _handle_start))
    application.add_handler(CommandHandler("ping", _handle_ping))
    application.add_handler(CommandHandler("online", _handle_online))
    application.add_handler(CommandHandler("offline", _handle_offline))
    application.add_handler(CommandHandler("status", _handle_status))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, _handle_message))

    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)

    try:
        while not _stop_event.is_set():
            await asyncio.sleep(0.5)
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


def _thread_main(config_path: str | Path) -> None:
    try:
        asyncio.run(_run_bot(config_path))
    except Exception:
        logging.exception("JARVIS Telegram secretary bot stopped")


def start_background(config_path: str | Path = CONFIG_FILE) -> threading.Thread:
    """Start the Telegram secretary bot in a daemon thread and return the thread."""
    global _thread
    if _thread and _thread.is_alive():
        return _thread
    _stop_event.clear()
    _thread = threading.Thread(
        target=_thread_main,
        args=(str(config_path),),
        name="JarvisTelegramSecretary",
        daemon=True,
    )
    _thread.start()
    return _thread


def stop_background() -> None:
    _stop_event.set()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    start_background()
    try:
        while True:
            threading.Event().wait(3600)
    except KeyboardInterrupt:
        stop_background()
