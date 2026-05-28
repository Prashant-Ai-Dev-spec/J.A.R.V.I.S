"""Background proactive check-ins for JARVIS."""

from __future__ import annotations

import datetime
import random
import threading
import time

try:
    import psutil
except Exception:
    psutil = None


MORNING_MSGS = [
    "Good morning bhai. Aaj ka plan kya hai?",
    "Subah ho gayi bhai. JEE prep ya project, kya pehle?",
    "JARVIS online hai bhai. Aaj ka mission bata.",
]

IDLE_MSGS = [
    "Bhai {minutes} minute se chup hai. Sab theek?",
    "Yaar {minutes} minute idle ho gaya. Kuch kaam hai kya?",
    "Main ready hoon bhai. Koi kaam dede.",
]

STUDY_MSGS = [
    "Bhai {time} ho gaya. Study window start karein?",
    "JEE prep ka time hai bhai. Chal shuru karte hain.",
    "Ye tera study slot hai bhai. Main ready hoon.",
]

BATTERY_MSGS = [
    "Bhai battery {pct}% pe hai. Charger laga le.",
    "Warning bhai, battery low hai: {pct}%.",
]

BREAK_MSGS = [
    "Bhai {mins} minute continuous ho gaye. 5 minute ka break le.",
    "Thoda paani pi le bhai. {mins} minute screen pe ho gaye.",
]

NIGHT_MSGS = [
    "Bhai kaafi raat ho gayi. So ja, kal fresh mind se kaam karenge.",
    "Raat zyada ho gayi bhai. Sleep bhi productivity ka part hai.",
]

CPU_MSGS = [
    "Bhai laptop thoda struggle kar raha hai. CPU {pct}% pe hai.",
    "Heavy process chal raha hai bhai. CPU {pct}%. Check karun?",
]

RANDOM_MSGS = [
    "Bhai kya chal raha hai? Kuch help chahiye?",
    "JARVIS idle hai bhai. Koi task hai toh bol.",
]


class ProactiveEngine:
    COOLDOWNS = {
        "morning": 60 * 60 * 8,
        "study": 60 * 60 * 2,
        "idle": 60 * 20,
        "battery": 60 * 15,
        "break": 60 * 60,
        "night": 60 * 60 * 6,
        "cpu": 60 * 10,
        "random": 60 * 90,
    }

    def __init__(self, jarvis_instance):
        self.jarvis = jarvis_instance
        self.cfg = jarvis_instance.cfg
        self.enabled = bool(self.cfg.get("proactive_enabled", True))
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_interaction = time.time()
        self._last_fired: dict[str, float] = {}
        self._session_start = time.time()
        self._custom_triggers: list[dict] = []
        self._study_times = self._parse_times(self.cfg.get("proactive_study_times", ["18:00", "20:00"]))
        self._morning_time = str(self.cfg.get("proactive_morning_time", "07:30") or "07:30")
        self._idle_threshold = max(1, int(self.cfg.get("proactive_idle_minutes", 20) or 20)) * 60
        self._listen_after_prompt = bool(self.cfg.get("proactive_listen_after_prompt", True))
        self._listen_timeout = max(1, int(self.cfg.get("proactive_listen_timeout_sec", 10) or 10))
        self._listen_phrase_limit = max(1, int(self.cfg.get("proactive_listen_phrase_limit", 12) or 12))
        self._listen_cue = str(
            self.cfg.get("proactive_listen_cue", "Bol bhai, 10 second sun raha hoon.")
            or "Bol bhai, 10 second sun raha hoon."
        )
        self._listen_after_prompt_delay = max(0.0, float(self.cfg.get("proactive_listen_after_prompt_delay", 1.0) or 1.0))
        self._last_prompt = ""
        self._last_followup = ""
        self._last_followup_at = ""
        self._last_followup_status = "never"
        print("  [OK] ProactiveEngine initialized.")

    def start(self) -> None:
        if not self.enabled:
            print("  [INFO] ProactiveEngine disabled in config.")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def ping(self) -> None:
        self._last_interaction = time.time()

    def set_enabled(self, enabled: bool) -> str:
        self.enabled = bool(enabled)
        if self.enabled:
            self.start()
            return "Proactive mode enabled bhai."
        self.stop()
        return "Proactive mode disabled bhai."

    def status(self) -> str:
        idle_min = int((time.time() - self._last_interaction) // 60)
        state = "enabled" if self.enabled else "disabled"
        study = ", ".join(self._study_times) or "none"
        follow_state = "enabled" if self._listen_after_prompt else "disabled"
        last_prompt = self._last_prompt or "none"
        last_heard = self._last_followup or "none"
        last_time = self._last_followup_at or "never"
        return (
            f"Proactive mode is {state}. Idle threshold {self._idle_threshold // 60} min, "
            f"current idle {idle_min} min, morning {self._morning_time}, study slots {study}. "
            f"Follow-up mic is {follow_state}, timeout {self._listen_timeout} sec. "
            f"Last prompt: {last_prompt}. Last follow-up: {last_heard}. "
            f"Follow-up status: {self._last_followup_status} at {last_time}."
        )

    def test(self) -> str:
        msg = "Haan bhai, proactive JARVIS online hai. Ab main zarurat padne par khud ping karunga."
        self._speak(msg)
        return msg

    def add_custom_trigger(self, name: str, message: str, hour: int, minute: int, cooldown_hours: int = 24) -> None:
        self.COOLDOWNS[name] = cooldown_hours * 3600
        self._custom_triggers.append({"name": name, "message": message, "hour": hour, "minute": minute})
        print(f"  [ProactiveEngine] Custom trigger '{name}' added at {hour:02d}:{minute:02d}")

    def _loop(self) -> None:
        time.sleep(15)
        while not self._stop_event.is_set():
            try:
                if self.enabled:
                    self._check_all()
            except Exception as exc:
                print(f"[ProactiveEngine] loop error: {exc}")
            self._stop_event.wait(60)

    def _check_all(self) -> None:
        now = datetime.datetime.now()
        h, m = now.hour, now.minute
        t_str = now.strftime("%H:%M")

        if self._should_fire("morning") and self._time_matches(self._morning_time, h, m):
            self._fire("morning", random.choice(MORNING_MSGS))
            return

        if self._should_fire("study"):
            for study_time in self._study_times:
                if self._time_matches(study_time, h, m):
                    self._fire("study", random.choice(STUDY_MSGS).replace("{time}", t_str))
                    return

        if self._should_fire("night") and 1 <= h < 4:
            self._fire("night", random.choice(NIGHT_MSGS))
            return

        if psutil and self._should_fire("battery"):
            try:
                battery = psutil.sensors_battery()
                if battery and not battery.power_plugged and battery.percent < 25:
                    self._fire("battery", random.choice(BATTERY_MSGS).replace("{pct}", str(int(battery.percent))))
                    return
            except Exception:
                pass

        if psutil and self._should_fire("cpu"):
            try:
                cpu = psutil.cpu_percent(interval=1)
                if cpu > 88:
                    self._fire("cpu", random.choice(CPU_MSGS).replace("{pct}", str(int(cpu))))
                    return
            except Exception:
                pass

        idle_secs = time.time() - self._last_interaction
        if self._should_fire("idle") and idle_secs > self._idle_threshold and not (h >= 23 or h < 7):
            msg = random.choice(IDLE_MSGS).replace("{minutes}", str(int(idle_secs // 60)))
            self._fire("idle", msg)
            return

        session_mins = int((time.time() - self._session_start) // 60)
        last_break = self._last_fired.get("break", 0)
        mins_since_break = int((time.time() - last_break) // 60) if last_break else session_mins
        if self._should_fire("break") and mins_since_break >= 60 and 8 <= h < 23:
            self._fire("break", random.choice(BREAK_MSGS).replace("{mins}", str(mins_since_break)))
            return

        for trigger in list(self._custom_triggers):
            name = trigger["name"]
            if self._should_fire(name) and h == trigger["hour"] and abs(m - trigger["minute"]) <= 2:
                self._fire(name, str(trigger["message"]))
                return

        if self._should_fire("random") and 10 <= h < 22 and random.random() < 0.3:
            self._fire("random", random.choice(RANDOM_MSGS))

    def _fire(self, trigger: str, message: str) -> None:
        self._speak(message)
        self._last_fired[trigger] = time.time()

    def _speak(self, text: str) -> None:
        print(f"\n[PROACTIVE] {text}\n")
        self._last_prompt = str(text or "").strip()
        self._last_followup_status = "prompt_spoken"
        self.jarvis.voice.speak(text)
        self._listen_for_followup(text)

    def _speech_wait_seconds(self, text: str) -> float:
        estimated = len(str(text or "")) / 24.0
        queued = 0.0
        try:
            q = getattr(self.jarvis.voice, "_tts_queue", None)
            queued = min(4.0, float(q.qsize()) * 1.2) if q is not None else 0.0
        except Exception:
            queued = 0.0
        return max(1.0, min(8.0, self._listen_after_prompt_delay + estimated + queued))

    def _listen_for_followup(self, prompt: str) -> None:
        """Open a short command window after proactive prompts."""
        if not self._listen_after_prompt or self._listen_timeout <= 0:
            self._last_followup_status = "disabled"
            return
        listen = getattr(self.jarvis.voice, "listen", None)
        if not callable(listen):
            self._last_followup_status = "listen_unavailable"
            print("[PROACTIVE FOLLOWUP] Voice listen() unavailable.")
            return
        try:
            time.sleep(self._speech_wait_seconds(prompt))
            print(f"[PROACTIVE FOLLOWUP] Cue: {self._listen_cue}")
            self.jarvis.voice.speak(self._listen_cue)
            time.sleep(self._speech_wait_seconds(self._listen_cue))

            self._last_followup_status = "listening"
            print(f"[PROACTIVE FOLLOWUP] Listening for {self._listen_timeout} sec...")
            heard = listen(timeout=self._listen_timeout, phrase_limit=self._listen_phrase_limit)
            heard = str(heard or "").strip()
            self._last_followup_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if not heard:
                self._last_followup_status = "no_input"
                self._last_followup = ""
                print("[PROACTIVE FOLLOWUP] No proactive follow-up heard.")
                return

            self._last_followup = heard
            self._last_followup_status = "heard"
            self.ping()
            print(f"\n[PROACTIVE FOLLOWUP] Heard: {heard}\n")
            self.jarvis.handle(heard)
        except Exception as exc:
            self._last_followup_status = f"error: {exc}"
            self._last_followup_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[ProactiveEngine] follow-up listen failed: {exc}")

    def _should_fire(self, trigger: str) -> bool:
        return (time.time() - self._last_fired.get(trigger, 0)) >= self.COOLDOWNS.get(trigger, 3600)

    @staticmethod
    def _parse_times(raw) -> list[str]:
        if isinstance(raw, str):
            raw = [item.strip() for item in raw.split(",")]
        return [str(item).strip() for item in (raw or []) if ProactiveEngine._valid_time(str(item).strip())]

    @staticmethod
    def _valid_time(value: str) -> bool:
        try:
            hour, minute = map(int, value.split(":", 1))
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except Exception:
            return False

    @staticmethod
    def _time_matches(value: str, hour: int, minute: int) -> bool:
        if not ProactiveEngine._valid_time(value):
            return False
        target_hour, target_minute = map(int, value.split(":", 1))
        return hour == target_hour and abs(minute - target_minute) <= 2
