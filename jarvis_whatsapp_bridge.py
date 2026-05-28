"""Local WhatsApp Web bridge coordinator for J.A.R.V.I.S.

The Node side owns WhatsApp Web. This Python side owns JARVIS voice prompts,
cooldowns, and the conservative ask-before-send policy.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "jarvis_config.json"
NODE_DIR = BASE_DIR / "jarvis-whatsapp"
NODE_SCRIPT = NODE_DIR / "whatsapp_bot.js"
RUNTIME_DIR = BASE_DIR / ".jarvis_runtime"
OUT_LOG = RUNTIME_DIR / "whatsapp_bridge.out.log"
ERR_LOG = RUNTIME_DIR / "whatsapp_bridge.err.log"

YES_WORDS = (
    "haan",
    "ha",
    "yes",
    "yep",
    "reply",
    "reply kar",
    "reply kr",
    "reply do",
    "kar do",
    "kr do",
    "bhej do",
    "send",
    "send kar",
    "send kr",
)
NO_WORDS = ("nahi", "nahin", "no", "mat", "cancel", "rehne do", "stop")
IGNORE_WORDS = ("ignore", "chhod", "chhor", "mat karo", "rehne do", "kuch nahi", "no", "nahi", "nahin")
DECLINE_WORDS = ("decline", "reject", "cut", "kaat", "kat", "utha mat", "call kaat", "call kat")
BUSY_WORDS = ("busy", "baad", "later", "default", "bol do", "busy bol")
REPLY_WORDS = ("reply", "message", "msg", "bhej", "send")


def _load_config(path: Path = CONFIG_FILE) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


def _post_json(url: str, payload: dict[str, Any], timeout: float = 8.0) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw else {}


def _get_json(url: str, timeout: float = 3.0) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw else {}


class WhatsAppBridge:
    def __init__(
        self,
        *,
        jarvis_factory: Callable[[], Any] | None = None,
        config_path: str | Path = CONFIG_FILE,
    ) -> None:
        self.jarvis_factory = jarvis_factory
        self.config_path = Path(config_path)
        self.cfg = _load_config(self.config_path)
        self.port = int(self.cfg.get("whatsapp_bridge_port", 3001) or 3001)
        self.mode = str(self.cfg.get("whatsapp_bridge_mode", "ask_first") or "ask_first")
        self.cooldown_sec = float(self.cfg.get("whatsapp_bridge_cooldown_sec", 5) or 5)
        self.call_cooldown_sec = float(self.cfg.get("whatsapp_bridge_call_cooldown_sec", 20) or 20)
        self.queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=100)
        self._seen: set[str] = set()
        self._last_by_sender: dict[str, float] = {}
        self._last_call_by_sender: dict[str, float] = {}
        self._stop = threading.Event()
        self._worker: threading.Thread | None = None
        self._process: subprocess.Popen | None = None
        self._last_event: dict[str, Any] | None = None
        self._last_send: dict[str, Any] | None = None
        self._last_call_action: dict[str, Any] | None = None
        self._active_calls: dict[str, dict[str, Any]] = {}
        self._call_lock = threading.RLock()
        self._last_error = ""

    def start(self) -> None:
        if bool(self.cfg.get("whatsapp_bridge_auto_start", True)):
            self.start_node()
        if not self._worker or not self._worker.is_alive():
            self._stop.clear()
            self._worker = threading.Thread(
                target=self._run,
                name="JarvisWhatsAppBridge",
                daemon=True,
            )
            self._worker.start()

    def start_node(self) -> bool:
        if self._process and self._process.poll() is None:
            return True
        if not NODE_SCRIPT.exists():
            self._last_error = f"Missing Node bridge: {NODE_SCRIPT}"
            return False
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.setdefault("JARVIS_WHATSAPP_PORT", str(self.port))
        env.setdefault(
            "JARVIS_WHATSAPP_INCOMING_URL",
            "http://127.0.0.1:8765/api/whatsapp/incoming",
        )
        if self.cfg.get("web_api_token") and not env.get("JARVIS_WEB_TOKEN"):
            env["JARVIS_WEB_TOKEN"] = str(self.cfg.get("web_api_token") or "")
        try:
            out = open(OUT_LOG, "a", encoding="utf-8")
            err = open(ERR_LOG, "a", encoding="utf-8")
            self._process = subprocess.Popen(
                ["node", str(NODE_SCRIPT)],
                cwd=str(NODE_DIR),
                stdout=out,
                stderr=err,
                env=env,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return True
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            return False

    def stop(self) -> None:
        self._stop.set()
        if self._process and self._process.poll() is None:
            self._process.terminate()

    def set_mode(self, mode: str) -> str:
        mode = str(mode or "").strip().lower()
        if mode not in {"ask_first", "notify_only", "paused"}:
            raise ValueError("mode must be ask_first, notify_only, or paused")
        self.mode = mode
        return self.mode

    def enqueue(self, event: dict[str, Any]) -> bool:
        event_id = str(event.get("id") or "")
        if event_id and event_id in self._seen:
            return False
        sender_id = str(event.get("from") or "").strip()
        now = time.time()
        is_call = str(event.get("event_type") or "").lower() == "call"
        if not is_call and sender_id and now - self._last_by_sender.get(sender_id, 0.0) < self.cooldown_sec:
            return False
        if event_id:
            self._seen.add(event_id)
            if len(self._seen) > 500:
                self._seen = set(list(self._seen)[-250:])
        if sender_id and not is_call:
            self._last_by_sender[sender_id] = now
        self.queue.put_nowait(event)
        return True

    def status(self) -> dict[str, Any]:
        node_status: dict[str, Any] = {}
        try:
            node_status = _get_json(f"http://127.0.0.1:{self.port}/status", timeout=1.5)
        except Exception as exc:
            node_status = {"ok": False, "error": str(exc)}
        process_running = bool(self._process and self._process.poll() is None)
        return {
            "enabled": bool(self.cfg.get("whatsapp_bridge_enabled", False)),
            "mode": self.mode,
            "port": self.port,
            "worker_running": bool(self._worker and self._worker.is_alive()),
            "process_running": process_running,
            "queue_size": self.queue.qsize(),
            "last_event": self._last_event,
            "last_send": self._last_send,
            "last_call_action": self._last_call_action,
            "active_calls": self.active_calls(),
            "last_error": self._last_error,
            "node": node_status,
            "logs": {
                "stdout": str(OUT_LOG),
                "stderr": str(ERR_LOG),
            },
        }

    def send_reply(self, to: str, text: str) -> dict[str, Any]:
        to = str(to or "").strip()
        text = str(text or "").strip()
        if not to or not text:
            raise ValueError("WhatsApp recipient and text are required")
        if "@g.us" in to:
            raise ValueError("Group replies are disabled")
        result = _post_json(
            f"http://127.0.0.1:{self.port}/send",
            {"to": to, "text": text},
            timeout=15.0,
        )
        if not result.get("ok"):
            raise RuntimeError(str(result.get("error") or "WhatsApp send failed"))
        self._last_send = {"to": to, "text": text, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "result": result}
        return result

    def reject_call(self, call_id: str) -> dict[str, Any]:
        call_id = str(call_id or "").strip()
        if not call_id:
            raise ValueError("Call id is required")
        result = _post_json(
            f"http://127.0.0.1:{self.port}/reject-call",
            {"id": call_id},
            timeout=8.0,
        )
        if not result.get("ok"):
            raise RuntimeError(str(result.get("error") or "WhatsApp call reject failed"))
        return result

    def active_calls(self) -> list[dict[str, Any]]:
        ttl = float(self.cfg.get("whatsapp_bridge_call_mobile_ttl_sec", 180) or 180)
        now = time.time()
        with self._call_lock:
            stale = [
                call_id
                for call_id, call in self._active_calls.items()
                if now - float(call.get("received_ts") or now) > ttl
            ]
            for call_id in stale:
                self._active_calls.pop(call_id, None)
            return sorted(
                (dict(call) for call in self._active_calls.values()),
                key=lambda call: float(call.get("received_ts") or 0),
                reverse=True,
            )

    def handle_call_action(self, call_id: str, action: str, text: str = "") -> dict[str, Any]:
        call_id = str(call_id or "").strip()
        action = str(action or "").strip().lower().replace("-", "_")
        text = " ".join(str(text or "").strip().split())
        if action == "reply":
            action = "reply_text"
        if action not in {"ignore", "decline", "busy", "reply_text"}:
            raise ValueError("action must be ignore, decline, busy, or reply_text")
        if not call_id:
            raise ValueError("call_id is required")

        with self._call_lock:
            call = dict(self._active_calls.get(call_id) or {})
        if not call:
            raise ValueError("Call not found or already handled")

        sender_id = str(call.get("from") or "").strip()
        if "@g.us" in sender_id:
            raise ValueError("Group calls are disabled")

        reply = ""
        if action == "busy":
            reply = str(
                self.cfg.get(
                    "whatsapp_bridge_call_default_reply",
                    "Bhai Prashant abhi busy hain, thodi der me call/message karenge.",
                )
                or ""
            ).strip()
        elif action == "reply_text":
            reply = text
            if not reply:
                raise ValueError("reply text is required")

        result: dict[str, Any] = {
            "ok": True,
            "call_id": call_id,
            "action": action,
            "sender": call.get("sender") or sender_id,
            "rejected": False,
            "sent": False,
        }
        if action == "ignore":
            result["status"] = "ignored"
            self._finish_call(call_id, result)
            return result

        try:
            result["reject_result"] = self.reject_call(call_id)
            result["rejected"] = True
        except Exception as exc:
            result["reject_error"] = str(exc)
            self._last_error = f"{type(exc).__name__}: {exc}"

        if reply:
            try:
                result["send_result"] = self.send_reply(sender_id, reply)
                result["sent"] = True
                result["reply"] = reply
            except Exception as exc:
                result["send_error"] = str(exc)
                self._last_error = f"{type(exc).__name__}: {exc}"

        if action == "decline" and not result["rejected"]:
            result["ok"] = False
            result["error"] = result.get("reject_error") or "Call decline failed"
        elif reply and not result["sent"]:
            result["ok"] = False
            result["error"] = result.get("send_error") or "Reply send failed"

        self._finish_call(call_id, result)
        return result

    def _remember_call(self, event: dict[str, Any]) -> dict[str, Any]:
        call_id = str(event.get("id") or "").strip()
        sender_id = str(event.get("from") or "").strip()
        record = {
            "call_id": call_id,
            "from": sender_id,
            "sender": self._clean_voice_text(event.get("sender") or sender_id or "unknown"),
            "is_video": bool(event.get("is_video", False)),
            "call_type": "video" if bool(event.get("is_video", False)) else "voice",
            "timestamp": event.get("timestamp"),
            "received_ts": time.time(),
            "received_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "ringing",
        }
        if call_id:
            with self._call_lock:
                self._active_calls[call_id] = record
        return record

    def _finish_call(self, call_id: str, result: dict[str, Any]) -> None:
        self._last_call_action = {
            **result,
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with self._call_lock:
            self._active_calls.pop(call_id, None)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                event = self.queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._handle_event(event)
            except Exception as exc:
                self._last_error = f"{type(exc).__name__}: {exc}"
            finally:
                self.queue.task_done()

    def _handle_event(self, event: dict[str, Any]) -> None:
        if str(event.get("event_type") or "").lower() == "call":
            self._handle_call_event(event)
            return

        self._last_event = {
            "from": event.get("from"),
            "sender": event.get("sender"),
            "message": event.get("message"),
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if self.mode == "paused":
            return

        jarvis = self.jarvis_factory() if callable(self.jarvis_factory) else None
        sender = self._clean_voice_text(event.get("sender") or event.get("from") or "kisi")
        message = self._clean_voice_text(event.get("message") or "")
        preview_len = int(self.cfg.get("whatsapp_bridge_read_message_chars", 140) or 140)
        message_preview = message[:preview_len].strip()
        if message_preview:
            prompt = f'Bhai WhatsApp pe {sender} se message aaya: "{message_preview}". Reply karu?'
        else:
            prompt = f"Bhai WhatsApp pe {sender} ka message aaya. Reply karu?"

        if self.mode == "notify_only":
            self._speak(jarvis, prompt)
            return

        answer = self._ask_voice(
            jarvis,
            prompt,
            retry_prompt="Bhai maine suna nahi. Reply karna hai to haan bolo, warna ignore.",
            timeout=int(self.cfg.get("whatsapp_bridge_message_confirm_timeout", 8)),
            phrase_limit=8,
        ).lower()
        if not self._is_yes(answer):
            return

        reply = self._clean_reply_command_prefix(
            self._ask_voice(
                jarvis,
                "Kya bolun?",
                retry_prompt="Bhai reply clear nahi aaya. Dobara bolo, kya bhejna hai?",
                timeout=int(self.cfg.get("whatsapp_bridge_message_reply_timeout", 15)),
                phrase_limit=18,
            )
        )
        if not reply:
            self._speak(jarvis, "Reply blank mila, cancel kar raha hoon.")
            return
        if self._is_no(reply.lower()):
            self._speak(jarvis, "Theek hai, reply cancel.")
            return

        try:
            self.send_reply(str(event.get("from") or ""), reply)
            self._speak(jarvis, "Reply bhej diya.")
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            self._speak(jarvis, "Bhai WhatsApp reply send nahi ho paya.")

    def _handle_call_event(self, event: dict[str, Any]) -> None:
        self._last_event = {
            "event_type": "call",
            "from": event.get("from"),
            "sender": event.get("sender"),
            "call_id": event.get("id"),
            "is_video": bool(event.get("is_video", False)),
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if not bool(self.cfg.get("whatsapp_bridge_call_secretary_enabled", True)):
            return
        if bool(self.cfg.get("whatsapp_bridge_call_ignore_groups", True)) and bool(event.get("is_group", False)):
            return
        if self.mode == "paused":
            return

        sender_id = str(event.get("from") or "")
        now = time.time()
        if sender_id and now - self._last_call_by_sender.get(sender_id, 0.0) < self.call_cooldown_sec:
            return
        if sender_id:
            self._last_call_by_sender[sender_id] = now

        jarvis = self.jarvis_factory() if callable(self.jarvis_factory) else None
        sender = self._clean_voice_text(event.get("sender") or event.get("from") or "kisi")
        call_kind = "video call" if bool(event.get("is_video", False)) else "voice call"
        call_id = str(event.get("id") or "").strip()
        self._remember_call(event)

        prompt = f"Bhai {sender} ka WhatsApp {call_kind} aa raha hai. Reply ya decline karu?"
        if bool(self.cfg.get("whatsapp_bridge_call_auto_reject", False)):
            self._speak(jarvis, prompt)
            try:
                self.reject_call(call_id)
                self._finish_call(call_id, {"ok": True, "call_id": call_id, "action": "auto_reject", "rejected": True, "sent": False})
                self._speak(jarvis, "Call decline kar diya.")
            except Exception as exc:
                self._last_error = f"{type(exc).__name__}: {exc}"
                self._speak(jarvis, "Bhai call decline nahi ho paya.")
            return

        answer = self._ask_voice(
            jarvis,
            prompt,
            retry_prompt="Bhai maine suna nahi. Call ke liye ignore, decline, busy, ya reply bolo.",
            timeout=int(self.cfg.get("whatsapp_bridge_call_confirm_timeout", 14)),
            phrase_limit=10,
        ).lower()
        if not answer:
            return
        if self._is_ignore_call(answer):
            self._finish_call(call_id, {"ok": True, "call_id": call_id, "action": "ignore", "rejected": False, "sent": False})
            return
        if call_id and not any(call.get("call_id") == call_id for call in self.active_calls()):
            return

        should_decline = self._is_decline_call(answer) or self._is_busy_call(answer) or self._is_reply_call(answer)
        if not should_decline:
            return

        reply = ""
        if self._is_busy_call(answer):
            reply = str(
                self.cfg.get(
                    "whatsapp_bridge_call_default_reply",
                    "Bhai Prashant abhi busy hain, thodi der me call/message karenge.",
                )
                or ""
            ).strip()
        elif self._is_reply_call(answer) and not self._is_decline_call(answer):
            reply = self._clean_reply_command_prefix(
                self._ask_voice(
                    jarvis,
                    "Kya message bhejun?",
                    retry_prompt="Bhai message clear nahi aaya. Dobara bolo, kya bhejna hai?",
                    timeout=int(self.cfg.get("whatsapp_bridge_call_reply_timeout", 20)),
                    phrase_limit=20,
                )
            )
            if not reply:
                self._speak(jarvis, "Reply blank mila, call ignore kar raha hoon.")
                return

        decline_ok = False
        try:
            self.reject_call(call_id)
            decline_ok = True
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"

        send_ok = True
        if reply:
            try:
                self.send_reply(sender_id, reply)
            except Exception as exc:
                send_ok = False
                self._last_error = f"{type(exc).__name__}: {exc}"

        self._finish_call(
            call_id,
            {
                "ok": bool(decline_ok and send_ok),
                "call_id": call_id,
                "action": "busy" if reply and self._is_busy_call(answer) else ("reply_text" if reply else "decline"),
                "sender": sender,
                "rejected": decline_ok,
                "sent": bool(reply and send_ok),
                "reply": reply,
            },
        )

        if decline_ok and send_ok and reply:
            self._speak(jarvis, "Call decline karke message bhej diya.")
        elif decline_ok and send_ok:
            self._speak(jarvis, "Call decline kar diya.")
        elif decline_ok and not send_ok:
            self._speak(jarvis, "Call decline ho gaya, par message send nahi ho paya.")
        else:
            self._speak(jarvis, "Bhai call decline nahi ho paya.")

    def _speak(self, jarvis: Any, text: str) -> None:
        voice = getattr(jarvis, "voice", jarvis)
        speak = getattr(voice, "speak", None)
        if callable(speak):
            speak(text)

    def _speech_wait_seconds(self, jarvis: Any, text: str) -> float:
        base = float(self.cfg.get("whatsapp_bridge_listen_after_prompt_delay", 1.0) or 1.0)
        estimated = len(str(text or "")) / 24.0
        queued = 0.0
        try:
            voice = getattr(jarvis, "voice", jarvis)
            q = getattr(voice, "_tts_queue", None)
            queued = min(4.0, float(q.qsize()) * 1.2) if q is not None else 0.0
        except Exception:
            queued = 0.0
        return max(1.3, min(8.0, base + estimated + queued))

    def _speak_and_wait(self, jarvis: Any, text: str) -> None:
        self._speak(jarvis, text)
        time.sleep(self._speech_wait_seconds(jarvis, text))

    def _ask_voice(self, jarvis: Any, prompt: str, *, retry_prompt: str, timeout: int, phrase_limit: int) -> str:
        attempts = max(1, int(self.cfg.get("whatsapp_bridge_voice_retries", 2) or 2))
        current_prompt = prompt
        for _attempt in range(attempts):
            self._speak_and_wait(jarvis, current_prompt)
            heard = self._listen(jarvis, timeout=timeout, phrase_limit=phrase_limit).strip()
            if heard:
                return heard
            current_prompt = retry_prompt
        return ""

    def _listen(self, jarvis: Any, timeout: int, phrase_limit: int) -> str:
        voice = getattr(jarvis, "voice", jarvis)
        listen = getattr(voice, "listen", None)
        if not callable(listen):
            return ""
        try:
            heard = listen(timeout=timeout, phrase_limit=phrase_limit)
        except TypeError:
            heard = listen(timeout=timeout)
        return str(heard or "").strip()

    def _is_yes(self, text: str) -> bool:
        return any(word in str(text or "").lower() for word in YES_WORDS)

    def _is_no(self, text: str) -> bool:
        return any(word in str(text or "").lower() for word in NO_WORDS)

    def _is_ignore_call(self, text: str) -> bool:
        return any(word in str(text or "").lower() for word in IGNORE_WORDS)

    def _is_decline_call(self, text: str) -> bool:
        return any(word in str(text or "").lower() for word in DECLINE_WORDS)

    def _is_busy_call(self, text: str) -> bool:
        return any(word in str(text or "").lower() for word in BUSY_WORDS)

    def _is_reply_call(self, text: str) -> bool:
        return any(word in str(text or "").lower() for word in REPLY_WORDS)

    def _clean_voice_text(self, text: Any) -> str:
        return " ".join(str(text or "").strip().split())[:100] or "unknown"

    def _clean_reply_command_prefix(self, text: Any) -> str:
        raw = " ".join(str(text or "").strip().split())
        lowered = raw.lower()
        prefixes = (
            "reply kardo ",
            "reply krdo ",
            "reply kar do ",
            "reply kr do ",
            "reply do ",
            "send kardo ",
            "send krdo ",
            "bhej do ",
        )
        for prefix in prefixes:
            if lowered.startswith(prefix):
                return raw[len(prefix):].strip(" \t:,-")
        return raw


_default_bridge: WhatsAppBridge | None = None


def get_bridge(jarvis_factory: Callable[[], Any] | None = None) -> WhatsAppBridge:
    global _default_bridge
    if _default_bridge is None:
        _default_bridge = WhatsAppBridge(jarvis_factory=jarvis_factory)
        if bool(_default_bridge.cfg.get("whatsapp_bridge_enabled", False)):
            _default_bridge.start()
    elif jarvis_factory and _default_bridge.jarvis_factory is None:
        _default_bridge.jarvis_factory = jarvis_factory
    return _default_bridge
