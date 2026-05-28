"""
╔══════════════════════════════════════════════════════════════╗
║   J.A.R.V.I.S — ProactiveEngine                             ║
║   JARVIS ab khud bolega — bina bulaye! 🤖                    ║
║   File: jarvis_modules/proactive_engine.py                   ║
╚══════════════════════════════════════════════════════════════╝

INSTALL:
    Is file ko   J.A.R.V.I.S/jarvis_modules/proactive_engine.py   mein rakh do.

JARVIS.py mein 4 changes:
    1. Top imports mein add karo (line ~29):
          from jarvis_modules.proactive_engine import ProactiveEngine

    2. JARVIS.__init__() mein last line ke baad (line ~5033):
          self.proactive = ProactiveEngine(self)
          self.proactive.start()

    3. JARVIS.handle() mein — function ke bilkul start mein (line ~5045 ke baad):
          self.proactive.ping()   # har command pe last_interaction update hoga

    4. jarvis_config.json mein add karo:
          "proactive_enabled": true,
          "proactive_study_times": ["18:00", "19:00", "20:00"],
          "proactive_morning_time": "07:30",
          "proactive_idle_minutes": 20
"""

import threading
import time
import datetime
import random
import platform

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


# ═══════════════════════════════════════════════════════════════
#  HINGLISH MESSAGES BANK
# ═══════════════════════════════════════════════════════════════

_MORNING_MSGS = [
    "Good morning bhai! Aaj ka din shuru karte hain — kya plan hai?",
    "Uth ja yaar, JARVIS online hai. Aaj kya karna hai bata!",
    "Subah ho gayi bhai! JEE prep ya project — kya pehle?",
    "Rise and shine! Main ready hoon — tu bata kab start karta hai.",
]

_IDLE_MSGS = [
    "Bhai kaafi time ho gaya — sab theek hai? Kuch kaam hai kya?",
    "Yaar {minutes} minute se tu chup hai — main hoon yahan agar kuch chahiye.",
    "Arre bhai, bata kuch kaam hai? Main idle pad raha hoon yahan! 😄",
    "Koi kaam dede yaar — main bhi bore ho raha hoon! 😂",
    "Hey bhai, alive hai na? Kuch bolunga toh?",
]

_STUDY_MSGS = [
    "Bhai study time ho gaya — JEE prep start karein?",
    "Yaar ye time toh roz padhta hai — aaj bhi? Main ready hoon!",
    "Bhai {time} ho gaya — ye tera study window hai. Chal shuru karte hain!",
    "JEE 2026 door nahi hai bhai — aaj ka session start karein?",
]

_BATTERY_MSGS = [
    "Bhai battery {pct}% pe aa gayi — charger laga le yaar!",
    "Warning bhai — battery low hai {pct}%. Kaam rukna nahi chahiye!",
    "Charger laga bhai — {pct}% bacha hai sirf!",
]

_BREAK_MSGS = [
    "Bhai {mins} minute se kaam kar raha hai — 5 min ka break le!",
    "Yaar thoda paani pi le — {mins} minute ho gaye screen pe!",
    "Break time bhai! {mins} minute continuous — aankhein rest karein thodi.",
    "Bhai uthke thoda stretch kar — {mins} minute ho gaye baithe baithe!",
]

_NIGHT_MSGS = [
    "Bhai kaafi raat ho gayi — so ja yaar. Kal fresh mind se padhna!",
    "1 baj gaye bhai — neend important hai JEE ke liye bhi!",
    "Yaar so ja ab — thaka hua dimaag kuch absorb nahi karta!",
]

_SYSTEM_HIGH_CPU = [
    "Bhai laptop thoda struggle kar raha hai — CPU {pct}% pe hai!",
    "Kuch heavy process chal raha hai — CPU {pct}%. Main check karun?",
]

_RANDOM_CHECKUP = [
    "Bhai kya chal raha hai? Kuch help chahiye kya?",
    "Yaar kuch interesting hua aaj? Bata na!",
    "Sab theek bhai? JARVIS idle hai — koi kaam dede! 😄",
]


# ═══════════════════════════════════════════════════════════════
#  PROACTIVE ENGINE
# ═══════════════════════════════════════════════════════════════

class ProactiveEngine:
    """
    JARVIS ka proactive brain —
    background mein chalta hai aur sahi time pe khud bolta hai.
    """

    # Kitne minute baad same trigger dobara fire ho sakta hai
    COOLDOWNS = {
        "morning":    60 * 60 * 8,   # 8 ghante (ek baar per din)
        "study":      60 * 60 * 2,   # 2 ghante
        "idle":       60 * 20,       # 20 min
        "battery":    60 * 15,       # 15 min
        "break":      60 * 60,       # 1 ghanta
        "night":      60 * 60 * 6,   # 6 ghante
        "cpu":        60 * 10,       # 10 min
        "random":     60 * 90,       # 1.5 ghante
    }

    def __init__(self, jarvis_instance):
        self.jarvis   = jarvis_instance
        self.cfg      = jarvis_instance.cfg
        self.enabled  = bool(self.cfg.get("proactive_enabled", True))

        self._thread          = None
        self._stop_event      = threading.Event()
        self._last_interaction = time.time()   # updated on every user command
        self._last_fired      = {}             # trigger_name -> timestamp
        self._session_start   = time.time()    # JARVIS start time

        # Config se study times
        raw_study = self.cfg.get("proactive_study_times", ["18:00", "20:00"])
        self._study_times = [t.strip() for t in raw_study]
        self._morning_time = self.cfg.get("proactive_morning_time", "07:30")
        self._idle_threshold = int(self.cfg.get("proactive_idle_minutes", 20)) * 60
        self._listen_after_prompt = bool(self.cfg.get("proactive_listen_after_prompt", True))
        self._listen_timeout = int(self.cfg.get("proactive_listen_timeout_sec", 10))
        self._listen_phrase_limit = int(self.cfg.get("proactive_listen_phrase_limit", 12))

        print("  [OK] ProactiveEngine initialized - JARVIS ab khud bolega!")

    # ── Public methods ────────────────────────────────────────

    def start(self):
        """Background thread start karo."""
        if not self.enabled:
            print("  [INFO] ProactiveEngine disabled in config.")
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Engine band karo."""
        self._stop_event.set()

    def ping(self):
        """Har user command pe ye call karo — last_interaction update hoga."""
        self._last_interaction = time.time()

    # ── Core loop ─────────────────────────────────────────────

    def _loop(self):
        """Har 60 second mein check karta hai — koi trigger fire karna hai kya."""
        time.sleep(15)  # Boot hone do pehle
        while not self._stop_event.is_set():
            try:
                self._check_all()
            except Exception as e:
                pass  # Koi bhi error loop nahi todega
            time.sleep(60)   # 1 min interval

    def _check_all(self):
        now   = datetime.datetime.now()
        h, m  = now.hour, now.minute
        t_str = now.strftime("%H:%M")

        # ── Morning briefing ──────────────────────────────────
        if self._should_fire("morning"):
            mh, mm = map(int, self._morning_time.split(":"))
            if h == mh and abs(m - mm) <= 2:
                self._speak(random.choice(_MORNING_MSGS))
                self._mark_fired("morning")
                return

        # ── Study time reminder ───────────────────────────────
        if self._should_fire("study"):
            for st in self._study_times:
                sh, sm = map(int, st.split(":"))
                if h == sh and abs(m - sm) <= 2:
                    msg = random.choice(_STUDY_MSGS).replace("{time}", t_str)
                    self._speak(msg)
                    self._mark_fired("study")
                    return

        # ── Night warning (raat 1 baje ke baad) ──────────────
        if self._should_fire("night") and (h >= 1 and h < 4):
            self._speak(random.choice(_NIGHT_MSGS))
            self._mark_fired("night")
            return

        # ── Battery check ─────────────────────────────────────
        if self._should_fire("battery") and _PSUTIL:
            try:
                batt = psutil.sensors_battery()
                if batt and not batt.power_plugged and batt.percent < 25:
                    msg = random.choice(_BATTERY_MSGS).replace("{pct}", str(int(batt.percent)))
                    self._speak(msg)
                    self._mark_fired("battery")
                    return
            except Exception:
                pass

        # ── High CPU alert ────────────────────────────────────
        if self._should_fire("cpu") and _PSUTIL:
            try:
                cpu = psutil.cpu_percent(interval=1)
                if cpu > 88:
                    msg = random.choice(_SYSTEM_HIGH_CPU).replace("{pct}", str(int(cpu)))
                    self._speak(msg)
                    self._mark_fired("cpu")
                    return
            except Exception:
                pass

        # ── Idle check ────────────────────────────────────────
        idle_secs = time.time() - self._last_interaction
        if self._should_fire("idle") and idle_secs > self._idle_threshold:
            # Raat ko idle message mat do (11pm - 7am)
            if not (h >= 23 or h < 7):
                idle_min = int(idle_secs // 60)
                msg = random.choice(_IDLE_MSGS).replace("{minutes}", str(idle_min))
                self._speak(msg)
                self._mark_fired("idle")
                return

        # ── Break reminder (1+ ghanta continuous kaam) ────────
        session_mins = int((time.time() - self._session_start) // 60)
        last_break = self._last_fired.get("break", 0)
        mins_since_break = int((time.time() - last_break) // 60) if last_break else session_mins
        if self._should_fire("break") and mins_since_break >= 60:
            # Sirf din mein (8am-11pm)
            if 8 <= h < 23:
                msg = random.choice(_BREAK_MSGS).replace("{mins}", str(mins_since_break))
                self._speak(msg)
                self._mark_fired("break")
                return

        # ── Random friendly check-in (bohot kam) ─────────────
        if self._should_fire("random"):
            # Sirf 10am-10pm ke beech, 30% chance
            if 10 <= h < 22 and random.random() < 0.3:
                self._speak(random.choice(_RANDOM_CHECKUP))
                self._mark_fired("random")

    # ── Helpers ───────────────────────────────────────────────

    def _speak(self, text: str):
        """JARVIS ki voice se bolao."""
        try:
            printable = str(text).encode("ascii", "replace").decode("ascii")
            print(f"\n[PROACTIVE] {printable}\n")
            self.jarvis.voice.speak(text)
            self._listen_for_followup(text)
        except Exception as e:
            print(f"[ProactiveEngine] speak failed: {e}")

    def _speech_wait_seconds(self, text: str) -> float:
        base = float(self.cfg.get("proactive_listen_after_prompt_delay", 1.0))
        estimated = len(str(text or "")) / 24.0
        queued = 0.0
        try:
            q = getattr(self.jarvis.voice, "_tts_queue", None)
            queued = min(4.0, float(q.qsize()) * 1.2) if q is not None else 0.0
        except Exception:
            queued = 0.0
        return max(1.3, min(8.0, base + estimated + queued))

    def _listen_for_followup(self, prompt: str):
        """Proactive prompt ke baad user ko short reply window do."""
        if not self._listen_after_prompt or self._listen_timeout <= 0:
            return
        try:
            listen = getattr(self.jarvis.voice, "listen", None)
            if not callable(listen):
                return
            time.sleep(self._speech_wait_seconds(prompt))
            heard = listen(timeout=self._listen_timeout, phrase_limit=self._listen_phrase_limit)
            heard = str(heard or "").strip()
            if not heard:
                return
            self.ping()
            print(f"\n[PROACTIVE FOLLOWUP] {heard}\n")
            self.jarvis.handle(heard)
        except Exception as e:
            print(f"[ProactiveEngine] follow-up listen failed: {e}")

    def _should_fire(self, trigger: str) -> bool:
        """Cooldown check — abhi fire karna chahiye ya nahi."""
        last = self._last_fired.get(trigger, 0)
        cooldown = self.COOLDOWNS.get(trigger, 3600)
        return (time.time() - last) >= cooldown

    def _mark_fired(self, trigger: str):
        """Trigger fire hua — timestamp save karo."""
        self._last_fired[trigger] = time.time()


# ═══════════════════════════════════════════════════════════════
#  CUSTOM TRIGGER (jarvis.py se call kar sakte ho)
# ═══════════════════════════════════════════════════════════════

    def add_custom_trigger(self, name: str, message: str, hour: int, minute: int, cooldown_hours: int = 24):
        """
        Apna custom trigger add karo runtime mein.

        Example:
            jarvis.proactive.add_custom_trigger(
                name    = "jee_reminder",
                message = "Bhai Physics chapter complete hua? Kal test hai!",
                hour    = 21,
                minute  = 0,
                cooldown_hours = 24
            )
        """
        self.COOLDOWNS[name] = cooldown_hours * 3600
        self._custom_triggers = getattr(self, "_custom_triggers", [])
        self._custom_triggers.append({
            "name": name, "message": message,
            "hour": hour, "minute": minute
        })
        print(f"  [ProactiveEngine] Custom trigger '{name}' added at {hour:02d}:{minute:02d}")
