"""
Background Windows notification secretary for J.A.R.V.I.S.

Import this module from jarvis.py and call:

    from jarvis_secretary import JarvisSecretary
    secretary = JarvisSecretary(jarvis_instance=self)
    secretary.start_background()

The class deliberately uses the existing JARVIS voice engine passed in through
jarvis_instance.voice.speak() and jarvis_instance.voice.listen().
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "jarvis_config.json"
DEFAULT_APPS = ["WhatsApp", "Instagram", "Snapchat", "Facebook", "Telegram"]
YES_WORDS = (
    "haan", "ha", "yes", "yep", "reply kar", "reply kr", "reply do",
    "kar do", "kr do", "bhej do", "send it", "send kar", "send kr",
)
NO_WORDS = ("nahi", "nahin", "no", "mat", "cancel", "rehne do", "stop")


@dataclass(frozen=True)
class NotificationEvent:
    app_name: str
    sender_name: str
    message: str = ""
    source: str = "windows"
    raw_id: str = ""


class JarvisSecretary:
    """Monitor selected Windows app notifications and offer voice-assisted replies."""

    def __init__(
        self,
        jarvis_instance: Any = None,
        *,
        config_path: str | Path = CONFIG_FILE,
        poll_interval: float = 2.0,
    ) -> None:
        self.jarvis = jarvis_instance
        self.config_path = Path(config_path)
        self.poll_interval = max(0.8, float(poll_interval or 2.0))
        self.cfg = self._load_config()
        self.apps = self._configured_apps()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._seen: set[str] = set()
        self._busy = threading.Lock()
        self._mode = "stopped"
        self._access_status = "unknown"
        self._last_error = ""
        self._last_event: NotificationEvent | None = None
        self._last_reply_action = ""

    def start_background(self) -> threading.Thread:
        """Start secretary monitoring in a daemon thread."""
        if self._thread and self._thread.is_alive():
            return self._thread
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="JarvisSecretary",
            daemon=True,
        )
        self._thread.start()
        return self._thread

    def stop(self) -> None:
        self._stop.set()

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def status(self) -> str:
        apps = ", ".join(self.apps)
        running = self.is_running()
        parts = [
            f"Windows notification secretary: {'RUNNING' if running else 'STOPPED'}",
            f"Mode: {self._mode}",
            f"Access: {self._access_status}",
            f"Apps: {apps}",
        ]
        if self._last_event:
            parts.append(
                "Last notification: "
                f"{self._last_event.app_name} / {self._last_event.sender_name}"
            )
        if self._last_reply_action:
            parts.append(f"Last reply action: {self._last_reply_action}")
        if self._last_error:
            parts.append(f"Last error: {self._last_error[:220]}")
        return "\n".join(parts)

    def _load_config(self) -> dict[str, Any]:
        try:
            if self.config_path.exists():
                return json.loads(self.config_path.read_text(encoding="utf-8"))
        except Exception:
            logging.exception("JarvisSecretary could not read config")
        return {}

    def _configured_apps(self) -> list[str]:
        raw = self.cfg.get("secretary_apps", DEFAULT_APPS)
        if isinstance(raw, str):
            raw = [item.strip() for item in raw.split(",")]
        apps = [str(item).strip() for item in raw if str(item).strip()]
        if bool(self.cfg.get("whatsapp_bridge_enabled", False)):
            apps = [app for app in apps if app.lower() != "whatsapp"]
            return apps or [app for app in DEFAULT_APPS if app.lower() != "whatsapp"]
        return apps or list(DEFAULT_APPS)

    def _run(self) -> None:
        try:
            if self._winrt_available():
                self._mode = "winrt"
                asyncio.run(self._winrt_monitor_loop())
            else:
                self._mode = "action-center-fallback"
                self._action_center_monitor_loop()
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            logging.exception("JarvisSecretary monitor stopped unexpectedly")
        finally:
            self._mode = "stopped"

    def _winrt_available(self) -> bool:
        try:
            import winrt.windows.ui.notifications.management  # noqa: F401
            import winrt.windows.ui.notifications  # noqa: F401
            return True
        except Exception as exc:
            self._last_error = f"WinRT incomplete: {type(exc).__name__}: {exc}"
            return False

    async def _winrt_monitor_loop(self) -> None:
        from winrt.windows.ui.notifications import NotificationKinds
        from winrt.windows.ui.notifications.management import UserNotificationListener

        listener = UserNotificationListener.current
        try:
            access = await listener.request_access_async()
            self._access_status = str(access).split(".")[-1]
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            logging.exception("Windows notification access request failed")
            self._access_status = "request_failed"

        while not self._stop.is_set():
            try:
                notifications = await listener.get_notifications_async(NotificationKinds.TOAST)
                for note in notifications:
                    event = self._event_from_winrt_notification(note)
                    if event and self._is_new(event):
                        self._handle_event(event)
            except Exception as exc:
                self._last_error = f"{type(exc).__name__}: {exc}"
                logging.exception("WinRT notification polling failed")
            await asyncio.sleep(self.poll_interval)

    def _event_from_winrt_notification(self, note: Any) -> NotificationEvent | None:
        app_name = self._safe_str(getattr(note, "app_info", None), "display_info", "display_name")
        if not app_name:
            app_name = self._safe_str(getattr(note, "app_info", None), "app_user_model_id")
        if not self._app_allowed(app_name):
            return None

        text_items = []
        try:
            bindings = note.notification.visual.bindings
            for binding in bindings:
                for item in binding.get_text_elements():
                    text_items.append(str(item.text or "").strip())
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            pass

        text_items = [item for item in text_items if item]
        sender = text_items[0] if text_items else app_name
        message = " ".join(text_items[1:]).strip()
        raw_id = f"winrt:{getattr(note, 'id', '')}:{app_name}:{sender}:{message}"
        return NotificationEvent(app_name=app_name, sender_name=sender, message=message, source="winrt", raw_id=raw_id)

    def _action_center_monitor_loop(self) -> None:
        """Fallback scanner for systems without WinRT notification listener packages.

        It reads visible Action Center text using pywinauto only when enabled by
        config key secretary_action_center_fallback. This avoids intrusive UI
        opening unless the user explicitly opts in.
        """
        if not bool(self.cfg.get("secretary_action_center_fallback", False)):
            self._access_status = "winrt_missing"
            self._speak(
                "Bhai secretary notification listener ready hai, par WinRT package missing hai. "
                "Full notification monitoring ke liye winrt install karna padega."
            )
            while not self._stop.is_set():
                time.sleep(5)
            return

        while not self._stop.is_set():
            try:
                for event in self._scan_action_center():
                    if self._is_new(event):
                        self._handle_event(event)
            except Exception:
                logging.exception("Action Center fallback scan failed")
            time.sleep(max(4.0, self.poll_interval))

    def _scan_action_center(self) -> list[NotificationEvent]:
        try:
            import pyautogui
            from pywinauto import Desktop
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            return []

        pyautogui.hotkey("win", "n")
        time.sleep(0.8)
        events: list[NotificationEvent] = []
        try:
            desktop = Desktop(backend="uia")
            text = "\n".join(ctrl.window_text() for ctrl in desktop.windows() if ctrl.window_text())
            for app in self.apps:
                if re.search(re.escape(app), text, re.I):
                    sender, message = self._parse_sender_message(text, app)
                    events.append(
                        NotificationEvent(
                            app_name=app,
                            sender_name=sender or "Unknown",
                            message=message,
                            source="action-center",
                            raw_id=f"action:{app}:{sender}:{message}",
                        )
                    )
        finally:
            try:
                pyautogui.press("esc")
            except Exception:
                pass
        return events

    def _parse_sender_message(self, text: str, app: str) -> tuple[str, str]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            if app.lower() in line.lower():
                sender = lines[idx + 1] if idx + 1 < len(lines) else "Unknown"
                message = lines[idx + 2] if idx + 2 < len(lines) else ""
                return sender, message
        return "Unknown", ""

    def _safe_str(self, obj: Any, *attrs: str) -> str:
        cur = obj
        try:
            for attr in attrs:
                cur = getattr(cur, attr)
                if callable(cur):
                    cur = cur()
            return str(cur or "").strip()
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            return ""

    def _app_allowed(self, app_name: str) -> bool:
        app_l = str(app_name or "").lower()
        return any(app.lower() in app_l or app_l in app.lower() for app in self.apps)

    def _is_new(self, event: NotificationEvent) -> bool:
        marker = event.raw_id or f"{event.app_name}:{event.sender_name}:{event.message}"
        if marker in self._seen:
            return False
        self._seen.add(marker)
        if len(self._seen) > 500:
            self._seen = set(list(self._seen)[-250:])
        return True

    def _handle_event(self, event: NotificationEvent) -> None:
        if not self._busy.acquire(blocking=False):
            return
        try:
            app = self._clean_voice_text(event.app_name)
            sender = self._clean_voice_text(event.sender_name or "kisi")
            self._last_event = event
            answer = self._ask_voice(
                f"Bhai {app} pe {sender} ka message aaya. Reply karu?",
                retry_prompt="Bhai maine suna nahi. Reply karna hai to haan bolo, warna no.",
                timeout=int(self.cfg.get("secretary_confirm_timeout", 9)),
                phrase_limit=8,
            ).lower()
            if not self._is_yes(answer):
                return

            reply = self._ask_voice(
                "Kya bolun?",
                retry_prompt="Bhai reply clear nahi aaya. Dobara bolo, kya bhejna hai?",
                timeout=int(self.cfg.get("secretary_reply_timeout", 15)),
                phrase_limit=18,
            ).strip()
            if not reply:
                self._speak("Reply blank mila, cancel kar raha hoon.")
                return
            reply = self._clean_reply_command_prefix(reply)
            if not reply:
                self._speak("Bhai reply text nahi mila, cancel kar raha hoon.")
                return
            if self._is_no(reply.lower()):
                self._speak("Theek hai, reply cancel.")
                return
            ok = self._open_and_send_reply(event, reply)
            self._speak("Reply bhej diya." if ok else "Bhai reply send nahi ho paya, app manually check kar lo.")
        finally:
            self._busy.release()

    def _is_yes(self, text: str) -> bool:
        return any(word in text for word in YES_WORDS)

    def _is_no(self, text: str) -> bool:
        return any(word in text for word in NO_WORDS)

    def _clean_reply_command_prefix(self, text: str) -> str:
        cleaned = str(text or "").strip()
        cleaned = re.sub(
            r"^(reply|replay)\s*(kar\s*do|kr\s*do|kardo|krdo|do)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip(" \t:,-")
        cleaned = re.sub(
            r"^(bhej\s*do|send\s*(kar\s*do|kr\s*do|kardo|krdo|it)?)\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip(" \t:,-")
        return cleaned

    def _speech_wait_seconds(self, text: str) -> float:
        base = float(self.cfg.get("secretary_listen_after_prompt_delay", 0.9))
        # speak() is queued/asynchronous in JARVIS, so wait long enough for the
        # short prompt to actually finish before opening the microphone.
        estimated = len(str(text or "")) / 24.0
        queued = 0.0
        try:
            voice = getattr(self.jarvis, "voice", self.jarvis)
            q = getattr(voice, "_tts_queue", None)
            queued = min(4.0, float(q.qsize()) * 1.2) if q is not None else 0.0
        except Exception:
            queued = 0.0
        return max(1.2, min(7.0, base + estimated + queued))

    def _speak_and_wait(self, text: str) -> None:
        self._speak(text)
        time.sleep(self._speech_wait_seconds(text))

    def _ask_voice(self, prompt: str, *, retry_prompt: str, timeout: int, phrase_limit: int) -> str:
        attempts = max(1, int(self.cfg.get("secretary_voice_retries", 2)))
        current_prompt = prompt
        for attempt in range(attempts):
            self._speak_and_wait(current_prompt)
            heard = (self._listen(timeout=timeout, phrase_limit=phrase_limit) or "").strip()
            if heard:
                return heard
            current_prompt = retry_prompt
        return ""

    def _speak(self, text: str) -> None:
        voice = getattr(self.jarvis, "voice", self.jarvis)
        speak = getattr(voice, "speak", None)
        if not callable(speak):
            raise RuntimeError("JarvisSecretary needs existing JARVIS speak() via jarvis_instance.voice.speak")
        speak(text)

    def _listen(self, timeout: int = 8, phrase_limit: int = 12) -> str | None:
        voice = getattr(self.jarvis, "voice", self.jarvis)
        listen = getattr(voice, "listen", None)
        if not callable(listen):
            raise RuntimeError("JarvisSecretary needs existing JARVIS listen() via jarvis_instance.voice.listen")
        try:
            return listen(timeout=timeout, phrase_limit=phrase_limit)
        except TypeError:
            return listen(timeout=timeout)

    def _open_and_send_reply(self, event: NotificationEvent, reply: str) -> bool:
        try:
            import pyautogui
            import pyperclip
        except Exception:
            return False

        opened_exact_notification = self._open_app_or_notification(event)
        if opened_exact_notification:
            self._wait_for_target_app(event, float(self.cfg.get("secretary_wait_for_app_timeout", 2.0)))
        time.sleep(float(self.cfg.get("secretary_reply_focus_delay", 0.35)))

        click = self.cfg.get("secretary_reply_click")
        if isinstance(click, (list, tuple)) and len(click) == 2:
            try:
                pyautogui.click(int(click[0]), int(click[1]))
                time.sleep(0.25)
                opened_exact_notification = True
                self._last_reply_action = "Used configured secretary_reply_click, then pasted reply."
            except Exception:
                pass

        if not opened_exact_notification and not click:
            self._last_reply_action = (
                "Reply focus not confirmed; not sending. Set secretary_reply_click or keep the notification visible."
            )
            return False
        elif opened_exact_notification:
            self._last_reply_action = self._last_reply_action or "Clicked matching Windows notification, then pasted reply."

        if opened_exact_notification and not click and bool(self.cfg.get("secretary_click_reply_box_after_open", True)):
            if not self._click_reply_box_in_active_window(event):
                self._last_reply_action = "Target app opened, but reply box focus was not confirmed."
                return False

        pyperclip.copy(reply)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.15)
        pyautogui.press("enter")
        return True

    def _open_app_or_notification(self, event: NotificationEvent) -> bool:
        if bool(self.cfg.get("secretary_open_notification_first", True)):
            if self._click_matching_notification(event):
                return True
            if bool(self.cfg.get("secretary_open_latest_notification_fallback", True)):
                if self._click_latest_notification(event):
                    return True

        app = event.app_name.lower()
        command = None
        app_routes = {
            "whatsapp": "start whatsapp:",
            "telegram": "start telegram",
            "instagram": "start https://www.instagram.com/direct/inbox/",
            "facebook": "start https://www.facebook.com/messages/",
            "snapchat": "start https://web.snapchat.com/",
        }
        for key, route in app_routes.items():
            if key in app:
                command = route
                break

        custom_routes = self.cfg.get("secretary_app_routes", {})
        if isinstance(custom_routes, dict):
            command = custom_routes.get(event.app_name) or custom_routes.get(app) or command

        if command:
            subprocess.Popen(command, shell=True)
            self._last_reply_action = "Opened app fallback; reply field was not confirmed."
            return False

        try:
            import pyautogui
            pyautogui.hotkey("win", "n")
            time.sleep(0.5)
            pyautogui.press("enter")
            return True
        except Exception:
            return False

    def _active_window_matches_app(self, event: NotificationEvent) -> bool:
        try:
            import pyautogui
            active = pyautogui.getActiveWindow()
            title = str(getattr(active, "title", "") or "").lower()
            app = str(event.app_name or "").lower()
            if not title or not app:
                return False
            return any(part in title for part in {app, app.replace(" ", ""), "whatsapp" if "whatsapp" in app else app})
        except Exception:
            return False

    def _wait_for_target_app(self, event: NotificationEvent, timeout: float) -> bool:
        deadline = time.time() + max(0.1, float(timeout or 0))
        while time.time() < deadline:
            if self._active_window_matches_app(event):
                return True
            time.sleep(0.12)
        return self._active_window_matches_app(event)

    def _click_reply_box_in_active_window(self, event: NotificationEvent) -> bool:
        try:
            import pyautogui
            active = pyautogui.getActiveWindow()
            if not active or not self._active_window_matches_app(event):
                return False
            if bool(self.cfg.get("secretary_press_escape_before_reply", True)):
                pyautogui.press("esc")
                time.sleep(0.12)

            if self._focus_reply_box_with_uia(event, active):
                return True

            ratio = self.cfg.get("secretary_reply_box_click_ratio", [0.5, 0.92])
            if not isinstance(ratio, (list, tuple)) or len(ratio) != 2:
                ratio = [0.62, 0.945]
            x = int(active.left + active.width * float(ratio[0]))
            y = int(active.top + active.height * float(ratio[1]))
            pyautogui.click(x, y)
            time.sleep(0.25)
            self._last_reply_action = f"{self._last_reply_action}; focused reply box by coordinate"
            return True
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            return False

    def _focus_reply_box_with_uia(self, event: NotificationEvent, active_window: Any) -> bool:
        try:
            import pyautogui
            from pywinauto import Desktop
        except Exception:
            return False

        try:
            handle = getattr(active_window, "_hWnd", None) or getattr(active_window, "hWnd", None)
            if handle:
                window = Desktop(backend="uia").window(handle=handle)
                controls = window.descendants()
            else:
                title = str(getattr(active_window, "title", "") or "")
                controls = Desktop(backend="uia").window(title=title).descendants()

            bottom_cutoff = active_window.top + active_window.height * 0.55
            candidates = []
            for ctrl in controls:
                try:
                    info = ctrl.element_info
                    control_type = str(getattr(info, "control_type", "") or "").lower()
                    name = re.sub(r"\s+", " ", ctrl.window_text() or "").strip()
                    lower = name.lower()
                    rect = ctrl.rectangle()
                    if rect.width() < 120 or rect.height() < 18:
                        continue
                    center_y = (rect.top + rect.bottom) / 2
                    if center_y < bottom_cutoff:
                        continue
                    if any(bad in lower for bad in ("search", "gif", "emoji", "sticker", "attach")):
                        continue
                    score = 0
                    if control_type in {"edit", "document"}:
                        score += 4
                    if any(word in lower for word in ("type a message", "message", "write a message")):
                        score += 5
                    if score <= 0:
                        continue
                    candidates.append((score, center_y, rect.width(), ctrl, name))
                except Exception:
                    continue

            if not candidates:
                return False
            candidates.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
            _score, _center_y, _width, ctrl, name = candidates[0]
            try:
                ctrl.click_input()
            except Exception:
                rect = ctrl.rectangle()
                pyautogui.click(int((rect.left + rect.right) / 2), int((rect.top + rect.bottom) / 2))
            time.sleep(0.2)
            self._last_reply_action = f"{self._last_reply_action}; focused reply box by UIA: {name[:60]}"
            return True
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            return False

    def _click_latest_notification(self, event: NotificationEvent) -> bool:
        """Best-effort fallback: click the newest notification card in Windows 11 panel."""
        try:
            import pyautogui
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            return False

        try:
            pyautogui.hotkey("win", "n")
            time.sleep(float(self.cfg.get("secretary_notification_open_delay", 0.9)))
            ratio = self.cfg.get("secretary_latest_notification_click_ratio", [0.84, 0.18])
            if not isinstance(ratio, (list, tuple)) or len(ratio) != 2:
                ratio = [0.84, 0.18]
            width, height = pyautogui.size()
            x = max(1, min(width - 1, int(width * float(ratio[0]))))
            y = max(1, min(height - 1, int(height * float(ratio[1]))))
            pyautogui.click(x, y)
            if self._wait_for_target_app(event, float(self.cfg.get("secretary_notification_click_delay", 0.7))):
                self._last_reply_action = "Clicked latest notification fallback, then pasted reply."
                return True
            self._last_reply_action = "Latest notification fallback did not focus the target app."
            return False
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            try:
                pyautogui.press("esc")
            except Exception:
                pass
            return False

    def _click_matching_notification(self, event: NotificationEvent) -> bool:
        try:
            import pyautogui
            from pywinauto import Desktop
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            return False

        needles = [
            str(event.sender_name or "").strip().lower(),
            str(event.message or "").strip().lower(),
            str(event.app_name or "").strip().lower(),
        ]
        needles = [item for item in needles if item and item not in {"unknown", "kisi"}]
        if not needles:
            return False

        try:
            pyautogui.hotkey("win", "n")
            time.sleep(float(self.cfg.get("secretary_notification_open_delay", 0.9)))
            desktop = Desktop(backend="uia")
            candidates = []
            for win in desktop.windows():
                try:
                    controls = win.descendants()
                except Exception:
                    controls = []
                for ctrl in controls:
                    try:
                        text = re.sub(r"\s+", " ", ctrl.window_text() or "").strip()
                        if not text:
                            continue
                        lower = text.lower()
                        score = 0
                        if event.sender_name and str(event.sender_name).lower() in lower:
                            score += 4
                        if event.message and str(event.message).lower()[:40] and str(event.message).lower()[:40] in lower:
                            score += 3
                        if event.app_name and str(event.app_name).lower() in lower:
                            score += 2
                        if not score and any(needle in lower for needle in needles):
                            score = 1
                        if score:
                            rect = ctrl.rectangle()
                            if rect.width() > 20 and rect.height() > 10:
                                candidates.append((score, rect.width() * rect.height(), ctrl, text))
                    except Exception:
                        continue

            if not candidates:
                pyautogui.press("esc")
                self._last_reply_action = "Matching notification not found; app fallback used."
                return False

            # Prefer the strongest text match, then the larger clickable surface.
            candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
            _score, _area, ctrl, text = candidates[0]
            try:
                ctrl.click_input()
            except Exception:
                rect = ctrl.rectangle()
                pyautogui.click(int((rect.left + rect.right) / 2), int((rect.top + rect.bottom) / 2))
            if self._wait_for_target_app(event, float(self.cfg.get("secretary_notification_click_delay", 0.7))):
                self._last_reply_action = f"Clicked notification match: {text[:120]}"
                return True
            self._last_reply_action = "Clicked a notification candidate, but target app did not focus."
            return False
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            try:
                pyautogui.press("esc")
            except Exception:
                pass
            return False

    def _clean_voice_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", str(text or "")).strip()
        return text[:80] or "unknown"


_default_secretary: JarvisSecretary | None = None


def start_background(jarvis_instance: Any, config_path: str | Path = CONFIG_FILE) -> threading.Thread:
    """Convenience function for main jarvis.py imports."""
    global _default_secretary
    if _default_secretary and _default_secretary.is_running():
        return _default_secretary._thread  # type: ignore[return-value]
    _default_secretary = JarvisSecretary(jarvis_instance=jarvis_instance, config_path=config_path)
    return _default_secretary.start_background()


def stop_background() -> None:
    if _default_secretary:
        _default_secretary.stop()
