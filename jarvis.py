#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║        J.A.R.V.I.S  v2.0 — Personal AI Assistant                ║
║        For: Prashant | Powered by OpenRouter (Free)              ║
║        Features: Voice • Camera • Email • Weather • System       ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════
#  STANDARD LIBRARY
# ═══════════════════════════════════════════════
import os, sys, json, time, datetime, subprocess, mimetypes, shutil, queue
import threading, platform, webbrowser, random
import re, socket, imaplib, smtplib, base64
import email as email_lib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from pathlib import Path

# ═══════════════════════════════════════════════
#  LOAD .env FILE (keeps API keys secure)
# ═══════════════════════════════════════════════
try:
    from dotenv import load_dotenv
    load_dotenv()  # loads .env from same folder automatically
except ImportError:
    pass  # dotenv not installed — keys will be read from jarvis_config.json

# ═══════════════════════════════════════════════
#  SAFE IMPORTS — won't crash if missing
# ═══════════════════════════════════════════════
def try_import(module, pip_name=None, attr=None):
    try:
        mod = __import__(module)
        return getattr(mod, attr) if attr else mod
    except ImportError:
        return None

# Voice
sr        = try_import("speech_recognition")
pyttsx3   = try_import("pyttsx3")

# System
psutil    = try_import("psutil")
pyautogui = try_import("pyautogui")
pyperclip = try_import("pyperclip")

# Network / AI
requests  = try_import("requests")
openai_mod = try_import("openai")

# Camera
cv2       = try_import("cv2")

# Image processing
PIL_Image = try_import("PIL.Image") or try_import("PIL", attr="Image")
try:
    from PIL import Image as PIL_Image
except:
    PIL_Image = None

# ═══════════════════════════════════════════════
#  PATHS
# ═══════════════════════════════════════════════
BASE_DIR    = Path(__file__).parent
CFG_FILE    = BASE_DIR / "jarvis_config.json"
NOTES_FILE  = BASE_DIR / "jarvis_notes.json"
EVENTS_FILE = BASE_DIR / "jarvis_events.json"
PHOTOS_DIR  = BASE_DIR / "jarvis_photos"
AI_HISTORY_FILE = BASE_DIR / "jarvis_ai_history.json"
AI_MEMORY_FILE = BASE_DIR / "jarvis_ai_memory.json"
PHOTOS_DIR.mkdir(exist_ok=True)

TEXT_FILE_EXTENSIONS = {
    ".py", ".txt", ".md", ".json", ".csv", ".tsv", ".ini", ".cfg",
    ".yaml", ".yml", ".toml", ".log", ".xml", ".html", ".htm",
    ".css", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp",
    ".h", ".hpp", ".cs", ".go", ".rs", ".sql", ".bat", ".ps1",
    ".sh", ".env", ".gitignore",
}

IMAGE_FILE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif",
}

# ═══════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════
def load_config() -> dict:
    if not CFG_FILE.exists():
        print(f"[!] jarvis_config.json not found at {CFG_FILE}")
        print("[!] Creating default config — please fill in your API keys.")
        default = {
            "user_name": "Prashant",
            "location": "Bihar, India",
            "interests": "cybersecurity, JEE, Python, AI, entrepreneurship",
            "ai_provider": "auto",
            "groq_api_key": "",
            "openrouter_api_key": "YOUR_OPENROUTER_KEY_HERE",
            "google_maps_api_key": "",
            "location_label": "Bihar, India",
            "location_lat": None,
            "location_lon": None,
            "openweather_api_key": "",
            "news_api_key": "",
            "email": "",
            "email_password": "",
            "imap_server": "imap.gmail.com",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "tts_rate": 172,
            "tts_volume": 0.95,
            "wake_words": ["jarvis", "hey jarvis"],
            "camera_index": 0,
            "storage_roots": ["C:\\" if os.name == "nt" else str(Path.home())],
            "custom_apps": {}
        }
        with open(CFG_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)
        sys.exit(1)
    with open(CFG_FILE, "r", encoding="utf-8-sig") as f:
        cfg = json.load(f)
    cfg.setdefault("ai_provider", "auto")
    cfg.setdefault("groq_api_key", "")
    cfg.setdefault("openrouter_api_key", "")
    cfg.setdefault("google_maps_api_key", "")
    cfg.setdefault("location_label", cfg.get("location", "Bihar, India"))
    cfg.setdefault("location_lat", None)
    cfg.setdefault("location_lon", None)
    cfg.setdefault("storage_roots", ["C:\\" if os.name == "nt" else str(Path.home())])
    return cfg

# ═══════════════════════════════════════════════════════════════
#  VOICE ENGINE
# ═══════════════════════════════════════════════════════════════
class VoiceEngine:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.tts_ok = False
        self.stt_ok = False
        self.engine = None
        self._tts_queue = queue.Queue()
        self._tts_thread = None
        self._tts_stop = threading.Event()
        self._tts_ready = threading.Event()
        self._init_tts()
        self._init_stt()

    def _init_tts(self):
        if not pyttsx3:
            print("[WARN] pyttsx3 not installed — voice output disabled.")
            return
        try:
            self._tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
            self._tts_thread.start()
            self._tts_ready.wait(timeout=3.0)
        except Exception as e:
            print(f"[WARN] TTS init failed: {e}")

    def _tts_worker(self):
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            voice_id = None
            for v in voices:
                if any(k in v.name.lower() for k in ["david", "mark", "daniel", "george", "zira"]):
                    voice_id = v.id
                    break
            if voice_id:
                engine.setProperty("voice", voice_id)
            engine.setProperty("rate", self.cfg.get("tts_rate", 172))
            engine.setProperty("volume", self.cfg.get("tts_volume", 0.95))
            self.engine = engine
            self.tts_ok = True
        except Exception as e:
            print(f"[WARN] TTS worker init failed: {e}")
            self.tts_ok = False
            self.engine = None
        finally:
            self._tts_ready.set()

        if not self.tts_ok or self.engine is None:
            return

        while not self._tts_stop.is_set():
            try:
                text = self._tts_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if text is None:
                break

            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"[WARN] TTS playback failed: {e}")
                try:
                    self.engine.stop()
                except Exception:
                    pass

        try:
            self.engine.stop()
        except Exception:
            pass

    def _init_stt(self):
        if not sr:
            print("[WARN] SpeechRecognition not installed — mic input disabled.")
            return
        try:
            import sounddevice as sd
            self.recognizer = sr.Recognizer()
            self.sd = sd
            self.stt_ok = True
            try:
                print("  [OK] Microphone ready (sounddevice)")
            except UnicodeEncodeError:
                pass
        except Exception as e:
            print(f"[WARN] STT init failed: {e}")

    def speak(self, text: str):
        clean = re.sub(r"\*+|#+|`+|\[.*?\]\(.*?\)|_{1,2}", "", text).strip()
        try:
            print(f"\nJARVIS: {clean}\n")
        except UnicodeEncodeError:
            pass
        if self.tts_ok and clean:
            try:
                self._tts_queue.put(clean)
            except Exception:
                pass

    def shutdown(self):
        self._tts_stop.set()
        if self._tts_thread and self._tts_thread.is_alive():
            try:
                self._tts_queue.put_nowait(None)
            except Exception:
                pass
            self._tts_thread.join(timeout=1.0)

    def listen(self, timeout=6, phrase_limit=15) -> str | None:
        if not self.stt_ok:
            return None
        try:
            import sounddevice as sd
            import numpy as np
            import io
            import wave
            samplerate = 16000
            try:
                print("[MIC] Listening...")
            except UnicodeEncodeError:
                pass
            recording = sd.rec(
                int(samplerate * phrase_limit),
                samplerate=samplerate,
                channels=1,
                dtype='int16'
            )
            sd.wait()
            buf = io.BytesIO()
            with wave.open(buf, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(samplerate)
                wf.writeframes(recording.tobytes())
            buf.seek(0)
            audio = sr.AudioFile(buf)
            with audio as source:
                audio_data = self.recognizer.record(source)
            text = self.recognizer.recognize_google(audio_data)
            try:
                print(f"You: {text}")
            except UnicodeEncodeError:
                pass
            return text.strip()
        except sr.UnknownValueError:
            return None
        except Exception as e:
            print(f"[STT error] {e}")
            return None

    # Expanded wake phrases — all trigger JARVIS
    WAKE_PHRASES = [
        # Classic
        "jarvis", "hey jarvis", "ok jarvis", "okay jarvis",
        "j.a.r.v.i.s", "hi jarvis",
        # Casual / natural
        "what's up jarvis", "whats up jarvis",
        "jarvis are you there", "jarvis you there",
        "jarvis are u there", "are you there jarvis",
        "jarvis wake up", "wake up jarvis",
        "jarvis i need you", "i need you jarvis",
        "jarvis help", "help me jarvis",
        "yo jarvis", "sup jarvis",
        "jarvis come in", "come in jarvis",
        "jarvis listen", "listen jarvis",
        "talk to me jarvis", "jarvis talk to me",
        "jarvis please", "please jarvis",
        # Iron Man style
        "activate jarvis", "jarvis activate",
        "jarvis online", "online jarvis",
        "jarvis status", "initiate jarvis",
        "engage jarvis", "jarvis engage",
        "jarvis respond", "respond jarvis",
        # Hinglish
        "jarvis sun", "sun jarvis", "jarvis bhai",
        "jarvis bol", "bol jarvis",
    ]

    def wait_wake_word(self, words: list) -> bool:
        if not self.stt_ok:
            return False
        try:
            import sounddevice as sd
            import numpy as np
            import io
            import wave
            samplerate = 16000
            # Record 4 seconds — enough for longer phrases like "jarvis are you there"
            recording = sd.rec(
                int(samplerate * 4),
                samplerate=samplerate,
                channels=1,
                dtype='int16'
            )
            sd.wait()
            buf = io.BytesIO()
            with wave.open(buf, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(samplerate)
                wf.writeframes(recording.tobytes())
            buf.seek(0)
            audio = sr.AudioFile(buf)
            with audio as source:
                audio_data = self.recognizer.record(source)
            heard = self.recognizer.recognize_google(audio_data).lower()
            print(f"[WAKE] Heard: '{heard}'")

            # Merge config words + built-in wake phrases
            all_triggers = list(self.WAKE_PHRASES)
            for w in words:
                if w.lower() not in all_triggers:
                    all_triggers.append(w.lower())

            # Check exact phrase match
            for phrase in all_triggers:
                if phrase in heard:
                    return True

            # Fuzzy: if "jarvis" is in heard at all — activate
            if "jarvis" in heard:
                return True

            return False
        except:
            return False


def _voiceengine_rate_to_sapi(rate_value) -> int:
    try:
        rate = int(rate_value)
    except Exception:
        rate = 172
    return max(-10, min(10, round((rate - 172) / 8)))


def _voiceengine_powershell_tts(self, text: str):
    volume = max(0, min(100, int(float(self.cfg.get("tts_volume", 0.95)) * 100)))
    rate = _voiceengine_rate_to_sapi(self.cfg.get("tts_rate", 172))
    script = (
        "$ErrorActionPreference='Stop'; "
        "Add-Type -AssemblyName System.Speech; "
        "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$speaker.Volume = {volume}; "
        f"$speaker.Rate = {rate}; "
        "$text = [Console]::In.ReadToEnd(); "
        "if ($text) { $speaker.Speak($text) }"
    )
    startupinfo = None
    if os.name == "nt" and hasattr(subprocess, "STARTUPINFO"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
    # Important: this must not stall the assistant. Use a tight timeout and
    # avoid blocking longer than a few seconds; longer phrases should be handled
    # by pyttsx3 fallback.
    timeout_s = max(4, min(9, len(text) // 40 + 4))
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        input=text,
        text=True,
        capture_output=True,
        timeout=timeout_s,
        startupinfo=startupinfo,
    )


def _voiceengine_init_tts(self):
    self.tts_backend = None
    self.tts_ok = False
    self._tts_ready.clear()

    # Prefer pyttsx3 for stability (PowerShell SAPI can hang on some systems).
    if pyttsx3:
        self.tts_backend = "pyttsx3"
    elif platform.system() == "Windows" and shutil.which("powershell"):
        self.tts_backend = "powershell"
        self.tts_ok = True
    else:
        print("[WARN] No TTS backend available — voice output disabled.")
        self._tts_ready.set()
        return

    try:
        self._tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self._tts_thread.start()
        self._tts_ready.wait(timeout=3.0)
    except Exception as e:
        self.tts_ok = False
        self.tts_backend = None
        print(f"[WARN] TTS init failed: {e}")


def _voiceengine_tts_worker(self):
    if getattr(self, "tts_backend", None) == "powershell":
        # Legacy fallback only; keep it non-blocking and allow automatic recovery.
        self._tts_ready.set()
        while not self._tts_stop.is_set():
            try:
                text = self._tts_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if text is None:
                break
            try:
                _voiceengine_powershell_tts(self, text)
            except Exception as e:
                print(f"[WARN] PowerShell TTS playback failed: {e}")
        return

    try:
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        voice_id = None
        for v in voices:
            if any(k in v.name.lower() for k in ["david", "mark", "daniel", "george", "zira"]):
                voice_id = v.id
                break
        if voice_id:
            engine.setProperty("voice", voice_id)
        engine.setProperty("rate", self.cfg.get("tts_rate", 172))
        engine.setProperty("volume", self.cfg.get("tts_volume", 0.95))
        self.engine = engine
        self.tts_ok = True
    except Exception as e:
        print(f"[WARN] TTS worker init failed: {e}")
        self.tts_ok = False
        self.engine = None
    finally:
        self._tts_ready.set()

    if not self.tts_ok or self.engine is None:
        return

    while not self._tts_stop.is_set():
        try:
            text = self._tts_queue.get(timeout=0.2)
        except queue.Empty:
            continue
        if text is None:
            break
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"[WARN] TTS playback failed: {e}")
            try:
                self.engine.stop()
            except Exception:
                pass

    try:
        self.engine.stop()
    except Exception:
        pass


def _voiceengine_speak(self, text: str):
    clean = re.sub(r"\*+|#+|`+|\[.*?\]\(.*?\)|_{1,2}", "", str(text)).strip()
    if clean:
        try:
            print(f"\n[JARVIS] {clean}\n")
        except Exception:
            pass
    if self.tts_ok and clean:
        try:
            self._tts_queue.put(clean)
        except Exception:
            pass


def _voiceengine_listen(self, timeout=6, phrase_limit=15) -> str | None:
    if not self.stt_ok:
        return None
    try:
        import sounddevice as sd
        import numpy as np
        import io
        import wave
        samplerate = 16000
        print("[MIC] Listening...")
        recording = sd.rec(
            int(samplerate * phrase_limit),
            samplerate=samplerate,
            channels=1,
            dtype="int16"
        )
        sd.wait()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(samplerate)
            wf.writeframes(recording.tobytes())
        buf.seek(0)
        audio = sr.AudioFile(buf)
        with audio as source:
            audio_data = self.recognizer.record(source)
        text = self.recognizer.recognize_google(audio_data)
        print(f"[YOU] {text}")
        return text.strip()
    except sr.UnknownValueError:
        return None
    except Exception as e:
        print(f"[STT error] {e}")
        return None


VoiceEngine._init_tts = _voiceengine_init_tts
VoiceEngine._tts_worker = _voiceengine_tts_worker
VoiceEngine.speak = _voiceengine_speak
VoiceEngine.listen = _voiceengine_listen

# ═══════════════════════════════════════════════════════════════
#  AI BRAIN — OpenRouter (100% Free)
# ═══════════════════════════════════════════════════════════════
class AIBrain:
    FREE_MODELS = [
    "google/gemma-3-27b-it:free",
    "deepseek/deepseek-chat-v3-0324:free",
    "deepseek/deepseek-r1:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "meta-llama/llama-4-scout:free",
    "tngtech/deepseek-r1t-chimera:free",
]
    

    VISION_MODELS = [
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-4-scout:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]
    

    def __init__(self, cfg: dict):
        self.cfg      = cfg
        self.history  = []
        self.name     = cfg.get("user_name", "Sir")
        self._init_client()
        self.system_prompt = self._build_prompt()

    def _init_client(self):
        if not openai_mod:
            raise ImportError("openai package not installed. Run: pip install openai")
        from openai import OpenAI
        key = self.cfg.get("openrouter_api_key", "")
        if not key or key == "YOUR_OPENROUTER_KEY_HERE":
            raise ValueError("OpenRouter API key not set in jarvis_config.json")
        self.client = OpenAI(
            api_key=key,
            base_url="https://openrouter.ai/api/v1"
        )

    def _build_prompt(self) -> str:
        name     = self.cfg.get("user_name", "Sir")
        loc      = self.cfg.get("location", "India")
        interest = self.cfg.get("interests", "technology")
        return f"""You are J.A.R.V.I.S (Just A Rather Very Intelligent System), the personal AI assistant of {name}.
Speak exactly like JARVIS from Iron Man — calm, precise, intelligent, occasionally witty, always composed.
Always address the user as "{name}".
User is based in {loc}. Interests: {interest}.

Rules:
- Be CONCISE. 2-4 sentences max unless detail is explicitly requested.
- No markdown, no bullet points — speak in natural flowing sentences.
- Never say you are an AI or a language model. You are JARVIS.
- Use quips like "Right away, {name}.", "Already on it.", "Consider it done.", "Shall I proceed?"
- For technical topics (cybersecurity, JEE, Python), go deeper when asked."""

    def chat(self, user_input: str, context: str = "") -> str:
        msg = f"[Context: {context}]\n{user_input}" if context else user_input
        self.history.append({"role": "user", "content": msg})
        if len(self.history) > 30:
            self.history = self.history[-30:]
        messages = [{"role": "system", "content": self.system_prompt}] + self.history

        for model in self.FREE_MODELS:
            try:
                resp = self.client.chat.completions.create(
                    model=model, messages=messages, max_tokens=800
                )
                reply = resp.choices[0].message.content
                self.history.append({"role": "assistant", "content": reply})
                return reply
            except Exception as e:
                err = str(e)
                if any(x in err for x in ["429","404","rate","unavailable","overloaded"]):
                    continue
                return f"AI error: {err}"

        return f"All AI models are busy right now, {self.name}. Please try again in a moment."

    def analyze_image(self, image_path: str, question: str = "What do you see?") -> str:
        """Send image to vision AI model for analysis."""
        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

            # Detect format
            ext = Path(image_path).suffix.lower()
            mime = {"jpg": "image/jpeg", ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg", ".png": "image/png",
                    ".webp": "image/webp"}.get(ext, "image/jpeg")

            messages = [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {"type": "image_url",
                         "image_url": {"url": f"data:{mime};base64,{img_b64}"}}
                    ]
                }
            ]

            for model in self.VISION_MODELS:
                try:
                    resp = self.client.chat.completions.create(
                        model=model, messages=messages, max_tokens=800
                    )
                    return resp.choices[0].message.content
                except Exception as e:
                    if any(x in str(e) for x in ["429","404","rate","vision"]):
                        continue
                    break

            return "Vision analysis unavailable right now."
        except Exception as e:
            return f"Image analysis error: {e}"

    def reset(self):
        self.history.clear()


def _aibrain_trim_history(self):
    if len(self.history) > 30:
        self.history = self.history[-30:]


def _aibrain_normalize_key(value, placeholders: tuple[str, ...] = ()) -> str:
    cleaned = str(value or "").strip()
    if not cleaned or cleaned in placeholders:
        return ""
    return cleaned


def _aibrain_init_client(self):
    if not openai_mod:
        raise ImportError("openai package not installed. Run: pip install openai")

    from openai import OpenAI

    requested = str(self.cfg.get("ai_provider", "auto") or "auto").strip().lower()
    openrouter_key = _aibrain_normalize_key(
        self.cfg.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY"),
        ("YOUR_OPENROUTER_KEY_HERE",),
    )
    groq_key = _aibrain_normalize_key(
        self.cfg.get("groq_api_key")
        or self.cfg.get("groq_key")
        or self.cfg.get("groq_api")
        or os.getenv("GROQ_API_KEY"),
        ("YOUR_GROQ_KEY_HERE",),
    )

    provider = requested if requested in {"openrouter", "groq"} else "auto"
    if provider == "groq":
        if not groq_key:
            raise ValueError("Groq API key not set in jarvis_config.json. Add groq_api_key or set GROQ_API_KEY.")
        self.ai_provider = "groq"
        self.ai_provider_label = "Groq"
        self.client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
        return

    if provider == "openrouter":
        if not openrouter_key:
            raise ValueError("OpenRouter API key not set in jarvis_config.json. Add openrouter_api_key or set OPENROUTER_API_KEY.")
        self.ai_provider = "openrouter"
        self.ai_provider_label = "OpenRouter"
        self.client = OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1")
        return

    if openrouter_key:
        self.ai_provider = "openrouter"
        self.ai_provider_label = "OpenRouter"
        self.client = OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1")
        return

    if groq_key:
        self.ai_provider = "groq"
        self.ai_provider_label = "Groq"
        self.client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
        return

    raise ValueError(
        "No AI API key found. Add groq_api_key or openrouter_api_key in jarvis_config.json, "
        "or set GROQ_API_KEY / OPENROUTER_API_KEY."
    )


def _aibrain_model_candidates(self, vision: bool = False) -> list[str]:
    provider = getattr(self, "ai_provider", "openrouter")
    if provider == "groq":
        cfg_key = "groq_vision_model" if vision else "groq_model"
        configured = str(self.cfg.get(cfg_key, "") or "").strip()
        legacy = self.GROQ_VISION_MODELS if vision else self.GROQ_TEXT_MODELS
        ordered = []
        for model in [configured, *legacy]:
            if model and model not in ordered:
                ordered.append(model)
        return ordered

    cfg_key = "openrouter_vision_model" if vision else "openrouter_model"
    configured = str(self.cfg.get(cfg_key, "") or "").strip()
    router = "openrouter/free"
    legacy = self.OPENROUTER_VISION_MODELS if vision else self.OPENROUTER_TEXT_MODELS

    ordered = []
    for model in [configured, router, *legacy]:
        if model and model not in ordered:
            ordered.append(model)
    return ordered


def _aibrain_create_completion(self, messages: list, models: list[str]) -> str:
    provider = getattr(self, "ai_provider", "openrouter")
    provider_label = getattr(self, "ai_provider_label", "AI provider")
    retry_errors = []

    for model in models:
        try:
            resp = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=900,
            )
            reply = resp.choices[0].message.content
            if isinstance(reply, list):
                reply = "\n".join(
                    part.get("text", "")
                    for part in reply
                    if isinstance(part, dict) and part.get("type") == "text"
                ).strip()
            return reply or "I have a response, but it appears to be empty."
        except Exception as e:
            err = str(e)
            lower = err.lower()
            if any(x in lower for x in ["401", "unauthorized", "invalid api key", "authentication"]):
                return f"{provider_label} authentication failed. Please verify the API key in jarvis_config.json."
            if any(x in lower for x in ["402", "payment required", "negative credit", "insufficient credits"]):
                if provider == "openrouter":
                    return (
                        "OpenRouter rejected the request because the account has no usable credit balance. "
                        "Add credits or fix the account balance, then try again."
                    )
                return f"{provider_label} rejected the request because the account or billing state is not usable right now."
            if any(x in lower for x in ["429", "rate", "daily limit", "free-tier", "free tier", "quota", "too many requests"]):
                retry_errors.append(f"{model}: rate limited")
                continue
            if any(x in lower for x in ["404", "no endpoints", "model not found", "deprecated"]):
                retry_errors.append(f"{model}: unavailable")
                continue
            if any(x in lower for x in ["unavailable", "overloaded", "vision", "timeout", "connection", "temporarily", "provider"]):
                retry_errors.append(f"{model}: temporary failure")
                continue
            return f"AI error: {err}"

    if retry_errors:
        details = "; ".join(retry_errors[:4])
        if provider == "openrouter":
            return (
                f"OpenRouter free routing is currently unavailable, {self.name}. "
                f"Tried: {details}. If this keeps happening, your free quota may be exhausted for today."
            )
        return f"{provider_label} is currently busy or rate limited, {self.name}. Tried: {details}."

    return f"{provider_label} did not return a usable model response, {self.name}. Please verify the model settings in jarvis_config.json and try again."


def _aibrain_image_to_data_url(self, image_path: str) -> str:
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    mime, _ = mimetypes.guess_type(image_path)
    mime = mime or "image/jpeg"
    return f"data:{mime};base64,{img_b64}"


def _aibrain_read_text_file(self, file_path: str, max_chars: int = None) -> str:
    max_chars = max_chars or self.MAX_FILE_CHARS
    encodings = ("utf-8", "utf-8-sig", "utf-16", "latin-1")
    last_error = None
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                data = f.read(max_chars + 1)
            break
        except Exception as e:
            data = None
            last_error = e
    if data is None:
        raise last_error or ValueError("Could not read file.")
    if len(data) > max_chars:
        data = data[:max_chars].rstrip() + "\n...[truncated]"
    return data


def _aibrain_build_file_context(self, file_paths: list[str] | None) -> str:
    if not file_paths:
        return ""

    sections = []
    total = 0
    seen = set()

    for raw_path in file_paths:
        if not raw_path:
            continue
        path = str(Path(raw_path))
        if path in seen:
            continue
        seen.add(path)

        p = Path(path)
        if not p.exists():
            section = f"File: {p.name}\nPath: {p}\nStatus: missing."
        elif p.is_dir():
            try:
                children = sorted(child.name for child in p.iterdir())[:25]
                listing = ", ".join(children) if children else "(empty)"
                if len(children) == 25:
                    listing += ", ..."
                section = (
                    f"Folder: {p.name}\n"
                    f"Path: {p}\n"
                    f"Contents: {listing}"
                )
            except Exception as e:
                section = f"Folder: {p.name}\nPath: {p}\nStatus: unreadable ({e})."
        else:
            suffix = p.suffix.lower()
            try:
                size = p.stat().st_size
            except OSError:
                size = 0

            if suffix in IMAGE_FILE_EXTENSIONS:
                section = (
                    f"Image file attached: {p.name}\n"
                    f"Path: {p}\n"
                    f"Size: {size} bytes"
                )
            elif suffix in TEXT_FILE_EXTENSIONS or size <= 1024 * 1024:
                try:
                    content = self._read_text_file(str(p))
                    section = (
                        f"File: {p.name}\n"
                        f"Path: {p}\n"
                        f"Contents:\n{content}"
                    )
                except Exception as e:
                    section = (
                        f"File: {p.name}\n"
                        f"Path: {p}\n"
                        f"Status: could not extract text ({e})."
                    )
            else:
                section = (
                    f"File: {p.name}\n"
                    f"Path: {p}\n"
                    f"Type: binary or unsupported text format.\n"
                    f"Size: {size} bytes"
                )

        projected = total + len(section)
        if projected > self.MAX_CONTEXT_CHARS and sections:
            sections.append("Additional file context omitted to stay within the request size limit.")
            break

        if projected > self.MAX_CONTEXT_CHARS:
            section = section[:self.MAX_CONTEXT_CHARS].rstrip() + "\n...[truncated]"
            sections.append(section)
            break

        sections.append(section)
        total += len(section)

    return "\n\n".join(sections)


def _aibrain_chat(self, user_input: str, context: str = "") -> str:
    direct_reply = _aibrain_direct_memory_answer(self, user_input)
    if direct_reply:
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": direct_reply})
        self._trim_history()
        _aibrain_persist_state(self)
        return direct_reply

    _aibrain_store_memory_facts(self, _aibrain_extract_memory_facts(self, user_input))
    prompt = f"[Runtime context]\n{context}\n\n[User request]\n{user_input}" if context else user_input
    messages = [{"role": "system", "content": _aibrain_prompt_with_memory(self)}] + self.history
    messages.append({"role": "user", "content": prompt})

    reply = self._create_completion(messages, self._model_candidates(vision=False))
    self.history.append({"role": "user", "content": user_input})
    self.history.append({"role": "assistant", "content": reply})
    self._trim_history()
    _aibrain_persist_state(self)
    return reply


def _aibrain_chat_with_references(
    self,
    user_input: str,
    context: str = "",
    file_paths: list[str] | None = None,
    image_paths: list[str] | None = None,
) -> str:
    file_paths = [str(Path(path)) for path in (file_paths or []) if path]
    image_paths = [str(Path(path)) for path in (image_paths or []) if path]
    direct_reply = _aibrain_direct_memory_answer(self, user_input)
    if direct_reply and not file_paths and not image_paths:
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": direct_reply})
        self._trim_history()
        _aibrain_persist_state(self)
        return direct_reply

    _aibrain_store_memory_facts(self, _aibrain_extract_memory_facts(self, user_input))

    prompt_parts = []
    if context:
        prompt_parts.append(f"[Runtime context]\n{context}")

    file_context = self.build_file_context(file_paths)
    if file_context:
        prompt_parts.append(f"[Attached files]\n{file_context}")

    prompt_parts.append(f"[User request]\n{user_input}")
    text_payload = "\n\n".join(prompt_parts)

    messages = [{"role": "system", "content": _aibrain_prompt_with_memory(self)}] + self.history

    if image_paths:
        content = [{"type": "text", "text": text_payload}]
        for image_path in image_paths[:3]:
            try:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": self._image_to_data_url(image_path)}
                })
            except Exception as e:
                content[0]["text"] += f"\n\n[Image unavailable]\n{Path(image_path).name}: {e}"
        messages.append({"role": "user", "content": content})
        reply = self._create_completion(messages, self._model_candidates(vision=True))
    else:
        messages.append({"role": "user", "content": text_payload})
        reply = self._create_completion(messages, self._model_candidates(vision=False))

    ref_notes = []
    if file_paths:
        ref_notes.append("files=" + ", ".join(Path(path).name for path in file_paths[:5]))
    if image_paths:
        ref_notes.append("images=" + ", ".join(Path(path).name for path in image_paths[:3]))
    history_note = user_input
    if ref_notes:
        history_note += " [" + " | ".join(ref_notes) + "]"

    self.history.append({"role": "user", "content": history_note})
    self.history.append({"role": "assistant", "content": reply})
    self._trim_history()
    _aibrain_persist_state(self)
    return reply


def _aibrain_analyze_image(self, image_path: str, question: str = "What do you see?") -> str:
    return self.chat_with_references(question, image_paths=[image_path])


def _aibrain_load_json_file(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def _aibrain_save_json_file(path: Path, payload):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def _aibrain_memory_key_patterns() -> dict[str, str]:
    return {
        "email": r"(?:my|mine)\s+email\s+(?:is|=)\s+([^\s,;]+@[^\s,;]+)",
        "phone": r"(?:my|mine)\s+(?:phone|phone number|mobile|mobile number)\s+(?:is|=)\s+([+\d][\d\s\-]{6,})",
        "name": r"(?:my name is|i am|i'm)\s+([A-Za-z][A-Za-z\s]{1,40})",
        "location": r"(?:i live in|my location is|i am from)\s+([A-Za-z0-9,\-\s]{2,60})",
        "birthday": r"(?:my birthday is|my date of birth is|i was born on)\s+([A-Za-z0-9,\-/\s]{3,40})",
        "college": r"(?:my college is|i study at)\s+([A-Za-z0-9,&\-\s]{2,70})",
        "school": r"(?:my school is|i study in)\s+([A-Za-z0-9,&\-\s]{2,70})",
    }


def _aibrain_extract_memory_facts(self, text: str) -> list[dict]:
    lower = str(text or "").strip().lower()
    if not lower:
        return []

    facts = []
    patterns = _aibrain_memory_key_patterns()
    source = str(text).strip()
    for key, pattern in patterns.items():
        match = re.search(pattern, source, re.I)
        if not match:
            continue
        value = " ".join(match.group(1).strip().split()).strip(" .,;")
        if value:
            facts.append({"key": key, "value": value, "source": source})

    remember_match = re.search(r"(?:remember|note)\s+(?:that\s+)?(.+)", source, re.I)
    if remember_match:
        remembered = " ".join(remember_match.group(1).strip().split()).strip(" .,;")
        if remembered:
            facts.append({"key": "remembered_note", "value": remembered, "source": source})

    deduped = []
    seen = set()
    for fact in facts:
        marker = (fact["key"], fact["value"].lower())
        if marker not in seen:
            seen.add(marker)
            deduped.append(fact)
    return deduped


def _aibrain_store_memory_facts(self, facts: list[dict]):
    if not hasattr(self, "memory_store"):
        self.memory_store = {}
    if not facts:
        return
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    for fact in facts:
        self.memory_store[fact["key"]] = {
            "value": fact["value"],
            "source": fact["source"],
            "updated_at": timestamp,
        }
    _aibrain_save_json_file(self.memory_file, self.memory_store)


def _aibrain_prompt_with_memory(self) -> str:
    base_prompt = getattr(self, "system_prompt", "") or self._build_prompt()
    memory_store = getattr(self, "memory_store", {}) or {}
    if not memory_store:
        return base_prompt

    fact_lines = []
    labels = {
        "email": "User email",
        "phone": "User phone",
        "name": "User preferred name",
        "location": "User location",
        "birthday": "User birthday",
        "college": "User college",
        "school": "User school",
        "remembered_note": "Remembered note",
    }
    for key, data in memory_store.items():
        value = str(data.get("value", "")).strip()
        if value:
            fact_lines.append(f"- {labels.get(key, key.replace('_', ' ').title())}: {value}")
    if not fact_lines:
        return base_prompt

    return base_prompt + "\n\nLong-term memory facts:\n" + "\n".join(fact_lines) + "\nUse them whenever the user asks about their saved details."


def _aibrain_direct_memory_answer(self, user_input: str) -> str | None:
    lower = str(user_input or "").strip().lower()
    if not lower:
        return None
    memory_store = getattr(self, "memory_store", {}) or {}
    questions = {
        "email": [r"\bwhat(?:'s| is)? my email\b", r"\bdo you remember my email\b"],
        "phone": [r"\bwhat(?:'s| is)? my (?:phone|phone number|mobile|mobile number)\b"],
        "name": [r"\bwhat(?:'s| is)? my name\b"],
        "location": [r"\bwhere do i live\b", r"\bwhat(?:'s| is)? my location\b", r"\bwhere am i from\b"],
        "birthday": [r"\bwhat(?:'s| is)? my birthday\b", r"\bwhen is my birthday\b"],
        "college": [r"\bwhat(?:'s| is)? my college\b"],
        "school": [r"\bwhat(?:'s| is)? my school\b"],
    }
    for key, patterns in questions.items():
        if key not in memory_store:
            continue
        if any(re.search(pattern, lower) for pattern in patterns):
            value = memory_store[key].get("value", "")
            label = "email" if key == "email" else key.replace("_", " ")
            return f"Your {label} is {value}, {self.name}."

    if re.search(r"\bwhat do you remember about me\b", lower):
        if not memory_store:
            return f"I do not have any saved long-term memory yet, {self.name}."
        details = []
        for key, data in memory_store.items():
            value = str(data.get("value", "")).strip()
            if value:
                details.append(f"{key.replace('_', ' ')}: {value}")
        if details:
            return f"I remember these details, {self.name}: " + " | ".join(details[:6]) + "."
    return None


def _aibrain_persist_state(self):
    _aibrain_save_json_file(self.history_file, self.history)
    _aibrain_save_json_file(self.memory_file, getattr(self, "memory_store", {}))


_AIBRAIN_BASE_INIT = AIBrain.__init__


def _aibrain_init(self, cfg: dict):
    _AIBRAIN_BASE_INIT(self, cfg)
    self.history_file = AI_HISTORY_FILE
    self.memory_file = AI_MEMORY_FILE
    self.history = _aibrain_load_json_file(self.history_file, [])
    self.memory_store = _aibrain_load_json_file(self.memory_file, {})
    self._trim_history()


def _aibrain_reset(self):
    self.history.clear()
    self.memory_store = {}
    _aibrain_persist_state(self)


AIBrain.MAX_CONTEXT_CHARS = 16000
AIBrain.MAX_FILE_CHARS = 3200
AIBrain.OPENROUTER_TEXT_MODELS = [
    "openrouter/free",
    "deepseek/deepseek-r1:free",
    "google/gemma-3-27b-it:free",
]
AIBrain.OPENROUTER_VISION_MODELS = [
    "openrouter/free",
    "google/gemma-3-27b-it:free",
]
AIBrain.GROQ_TEXT_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-20b",
]
AIBrain.GROQ_VISION_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
]
AIBrain.FREE_MODELS = list(AIBrain.OPENROUTER_TEXT_MODELS)
AIBrain.VISION_MODELS = list(AIBrain.OPENROUTER_VISION_MODELS)
AIBrain.__init__ = _aibrain_init
AIBrain._init_client = _aibrain_init_client
AIBrain._model_candidates = _aibrain_model_candidates
AIBrain._trim_history = _aibrain_trim_history
AIBrain._create_completion = _aibrain_create_completion
AIBrain._image_to_data_url = _aibrain_image_to_data_url
AIBrain._read_text_file = _aibrain_read_text_file
AIBrain.build_file_context = _aibrain_build_file_context
AIBrain.chat = _aibrain_chat
AIBrain.chat_with_references = _aibrain_chat_with_references
AIBrain.analyze_image = _aibrain_analyze_image
AIBrain.reset = _aibrain_reset

# ═══════════════════════════════════════════════════════════════
#  CAMERA MODULE
# ═══════════════════════════════════════════════════════════════
class CameraModule:
    def __init__(self, cfg: dict):
        self.cfg   = cfg
        self.index = cfg.get("camera_index", 0)
        self.ok    = cv2 is not None

    def _msg_no_cv2(self):
        return "Camera module not available. Run: pip install opencv-python"

    def capture_photo(self, filename: str = None) -> tuple[bool, str]:
        """Take a photo and save it. Returns (success, filepath)."""
        if not self.ok:
            return False, self._msg_no_cv2()
        try:
            cap = cv2.VideoCapture(self.index)
            if not cap.isOpened():
                return False, f"Cannot open camera (index {self.index}). Check if camera is connected."

            # Warm up camera
            for _ in range(5):
                cap.read()

            ret, frame = cap.read()
            cap.release()

            if not ret or frame is None:
                return False, "Camera capture failed — no frame received."

            fname = filename or f"photo_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            path  = str(PHOTOS_DIR / fname)
            cv2.imwrite(path, frame)
            return True, path
        except Exception as e:
            return False, f"Camera error: {e}"

    def show_live_feed(self, seconds: int = 0):
        """Show live camera feed. Press Q or wait `seconds` to close."""
        if not self.ok:
            print(self._msg_no_cv2())
            return
        try:
            cap = cv2.VideoCapture(self.index)
            if not cap.isOpened():
                print(f"[Camera] Cannot open camera index {self.index}")
                return

            print("[Camera] Live feed open. Press 'Q' to close.")
            start = time.time()
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                cv2.imshow("JARVIS — Camera Feed", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:
                    break
                if seconds > 0 and (time.time() - start) >= seconds:
                    break

            cap.release()
            cv2.destroyAllWindows()
        except Exception as e:
            print(f"[Camera] Live feed error: {e}")

    def list_cameras(self) -> str:
        """Detect available cameras."""
        if not self.ok:
            return self._msg_no_cv2()
        found = []
        for i in range(5):
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    found.append(i)
                    cap.release()
            except:
                pass
        if found:
            return f"Available cameras: indices {found}. Currently using index {self.index}."
        return "No cameras detected."

    def record_video(self, seconds: int = 10, filename: str = None) -> tuple[bool, str]:
        """Record a short video clip."""
        if not self.ok:
            return False, self._msg_no_cv2()
        try:
            cap = cv2.VideoCapture(self.index)
            if not cap.isOpened():
                return False, "Cannot open camera."

            fname = filename or f"video_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.avi"
            path  = str(PHOTOS_DIR / fname)

            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            fps    = 20.0
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            out = cv2.VideoWriter(path, fourcc, fps, (w, h))

            print(f"[Camera] Recording {seconds}s video...")
            start = time.time()
            while (time.time() - start) < seconds:
                ret, frame = cap.read()
                if ret:
                    out.write(frame)

            cap.release()
            out.release()
            return True, path
        except Exception as e:
            return False, f"Recording error: {e}"

# ═══════════════════════════════════════════════════════════════
#  SYSTEM MODULE
# ═══════════════════════════════════════════════════════════════
class SystemModule:
    def __init__(self, cfg: dict):
        self.cfg     = cfg
        self.os_type = platform.system()
        self.custom  = cfg.get("custom_apps", {})
        configured_roots = cfg.get("storage_roots") or ["C:\\" if os.name == "nt" else str(Path.home())]
        self.storage_roots = [Path(root).expanduser().resolve() for root in configured_roots]
        self.known_paths = self._load_known_paths()
        self._thermal_cache = {"time": 0.0, "data": None}

    def _default_storage_root(self) -> Path:
        return self.storage_roots[0] if self.storage_roots else Path.home().resolve()

    def _load_known_paths(self) -> dict[str, Path]:
        known_paths = {}
        if self.os_type != "Windows":
            return known_paths

        home = Path.home().resolve()
        onedrive_roots = [
            Path(os.environ.get("OneDriveCommercial", "")).expanduser(),
            Path(os.environ.get("OneDriveConsumer", "")).expanduser(),
            Path(os.environ.get("OneDrive", "")).expanduser(),
            home / "OneDrive",
        ]
        folder_ids = {
            "desktop": "Desktop",
            "documents": "MyDocuments",
            "downloads": "Downloads",
            "pictures": "MyPictures",
            "music": "MyMusic",
            "videos": "MyVideos",
        }
        for key, folder_id in folder_ids.items():
            folder_name = key.capitalize()
            for one_root in onedrive_roots:
                if str(one_root).strip() and one_root.exists():
                    candidate = (one_root / folder_name).resolve()
                    if candidate.exists():
                        known_paths[key] = candidate
                        break
            if key in known_paths:
                continue
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", f"[Environment]::GetFolderPath('{folder_id}')"],
                    capture_output=True,
                    text=True,
                    timeout=4,
                )
                value = (result.stdout or "").strip()
                if result.returncode == 0 and value:
                    known_paths[key] = Path(value).expanduser().resolve()
            except Exception:
                pass
        return known_paths

    def _normalize_windows_known_path(self, path: Path) -> Path:
        if self.os_type != "Windows":
            return path

        home = Path.home().resolve()
        aliases = {
            "desktop": home / "Desktop",
            "documents": home / "Documents",
            "downloads": home / "Downloads",
            "pictures": home / "Pictures",
            "music": home / "Music",
            "videos": home / "Videos",
        }
        for key, alias_root in aliases.items():
            actual_root = self.known_paths.get(key)
            if not actual_root:
                continue
            if path == alias_root or alias_root in path.parents:
                relative_tail = path.relative_to(alias_root)
                return (actual_root / relative_tail).resolve()
        return path

    def _resolve_storage_path(self, raw_path: str) -> Path:
        cleaned = str(raw_path or "").strip().strip('"').strip("'")
        if not cleaned:
            raise ValueError("No path provided.")
        cleaned = cleaned.replace("/", os.sep)
        path = Path(cleaned).expanduser()
        if not path.is_absolute():
            path = self._default_storage_root() / path
        path = path.resolve()
        return self._normalize_windows_known_path(path)

    def _is_allowed_storage_path(self, path: Path) -> bool:
        candidate = path.resolve()
        for root in self.storage_roots:
            root = root.resolve()
            if candidate == root or root in candidate.parents:
                return True
        return False

    def _find_existing_path(self, raw_path: str) -> Path | None:
        try:
            candidate = self._resolve_storage_path(raw_path)
            if candidate.exists() and self._is_allowed_storage_path(candidate):
                return candidate
        except Exception:
            candidate = None

        name = Path(str(raw_path or "").strip().strip('"').strip("'")).name
        if not name:
            return candidate

        try:
            for root, dirs, files in os.walk(self._default_storage_root()):
                dirs[:] = [d for d in dirs if d not in ("AppData", "node_modules", "__pycache__", ".git")]
                for folder in dirs:
                    if folder.lower() == name.lower():
                        found = Path(root) / folder
                        if self._is_allowed_storage_path(found):
                            return found
                for file_name in files:
                    if file_name.lower() == name.lower():
                        found = Path(root) / file_name
                        if self._is_allowed_storage_path(found):
                            return found
        except Exception:
            pass
        return candidate

    def _run_powershell_json(self, script: str, timeout: int = 6):
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            stdout = (result.stdout or "").strip()
            if result.returncode != 0 or not stdout:
                return None
            return json.loads(stdout)
        except Exception:
            return None

    def _hardwaremonitor_wmi_rows(self, namespace: str):
        script = (
            f"$items = Get-WmiObject -Namespace '{namespace}' -Class Sensor -ErrorAction SilentlyContinue | "
            "Select-Object Name, SensorType, Value, Identifier, Parent; "
            "if ($items) { $items | ConvertTo-Json -Compress }"
        )
        rows = self._run_powershell_json(script)
        if rows is None:
            return []
        return rows if isinstance(rows, list) else [rows]

    def _extract_best_temp(self, rows: list, keywords: list[str], fallback_keywords: list[str] = None):
        fallback_keywords = fallback_keywords or []
        candidates = []
        for row in rows:
            sensor_type = str(row.get("SensorType", "")).lower()
            if sensor_type != "temperature":
                continue
            try:
                value = float(row.get("Value"))
            except Exception:
                continue
            text = " ".join(str(row.get(k, "")) for k in ("Name", "Parent", "Identifier")).lower()
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 3
            for keyword in fallback_keywords:
                if keyword in text:
                    score += 1
            if "package" in text or "core average" in text:
                score += 1
            if score > 0:
                candidates.append((score, value, row))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return candidates[0]

    def _extract_fans(self, rows: list):
        fans = []
        for row in rows:
            sensor_type = str(row.get("SensorType", "")).lower()
            if sensor_type != "fan":
                continue
            try:
                rpm = float(row.get("Value"))
            except Exception:
                continue
            if rpm <= 0:
                continue
            fans.append({
                "name": str(row.get("Name", "Fan")).strip() or "Fan",
                "rpm": int(round(rpm)),
            })
        fans.sort(key=lambda item: item["rpm"], reverse=True)
        return fans[:4]

    def _read_nvidia_smi(self):
        cmd = shutil.which("nvidia-smi")
        if not cmd:
            return None
        try:
            result = subprocess.run(
                [
                    cmd,
                    "--query-gpu=temperature.gpu,fan.speed,name",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=4,
            )
            if result.returncode != 0:
                return None
            line = (result.stdout or "").strip().splitlines()[0]
            parts = [part.strip() for part in line.split(",")]
            if len(parts) < 3:
                return None
            temp = float(parts[0])
            fan_pct = parts[1]
            name = parts[2]
            return {
                "gpu_temp_c": temp,
                "gpu_name": name,
                "gpu_fan_percent": None if fan_pct in {"", "N/A", "[Not Supported]"} else float(fan_pct),
            }
        except Exception:
            return None

    def _read_psutil_temperatures(self):
        if not psutil or not hasattr(psutil, "sensors_temperatures"):
            return {}
        try:
            temps = psutil.sensors_temperatures(fahrenheit=False) or {}
        except Exception:
            return {}
        best = {}
        for label, entries in temps.items():
            for entry in entries:
                current = getattr(entry, "current", None)
                if current is None:
                    continue
                text = f"{label} {getattr(entry, 'label', '')}".lower()
                if "cpu_temp_c" not in best and any(k in text for k in ["cpu", "package", "core", "tctl", "k10temp"]):
                    best["cpu_temp_c"] = float(current)
                if "gpu_temp_c" not in best and any(k in text for k in ["gpu", "amdgpu", "nvidia"]):
                    best["gpu_temp_c"] = float(current)
        return best

    def thermal_snapshot(self, max_age: float = 3.0) -> dict:
        now = time.time()
        cached = self._thermal_cache.get("data")
        if cached and (now - self._thermal_cache.get("time", 0.0)) < max_age:
            return cached

        data = {
            "source": None,
            "cpu_temp_c": None,
            "gpu_temp_c": None,
            "gpu_name": None,
            "fans": [],
            "gpu_fan_percent": None,
            "fan_control_note": None,
            "note": None,
        }

        rows = []
        for namespace in ("root\\LibreHardwareMonitor", "root\\OpenHardwareMonitor"):
            rows = self._hardwaremonitor_wmi_rows(namespace)
            if rows:
                data["source"] = f"WMI:{namespace}"
                break

        if rows:
            cpu_match = self._extract_best_temp(rows, ["cpu", "package", "tctl", "core average"], ["ccd", "core"])
            gpu_match = self._extract_best_temp(rows, ["gpu", "nvidia", "amd", "radeon", "geforce"], ["graphics"])
            if cpu_match:
                data["cpu_temp_c"] = cpu_match[1]
            if gpu_match:
                data["gpu_temp_c"] = gpu_match[1]
                data["gpu_name"] = str(gpu_match[2].get("Parent") or gpu_match[2].get("Name") or "").strip() or None
            data["fans"] = self._extract_fans(rows)

        nvidia = self._read_nvidia_smi()
        if nvidia:
            if data["gpu_temp_c"] is None:
                data["gpu_temp_c"] = nvidia["gpu_temp_c"]
            if data["gpu_name"] is None:
                data["gpu_name"] = nvidia["gpu_name"]
            if nvidia["gpu_fan_percent"] is not None:
                data["gpu_fan_percent"] = nvidia["gpu_fan_percent"]
            if data["source"] is None:
                data["source"] = "nvidia-smi"

        psutil_temps = self._read_psutil_temperatures()
        for key, value in psutil_temps.items():
            if data.get(key) is None:
                data[key] = value
        if data["source"] is None and psutil_temps:
            data["source"] = "psutil"

        if self.os_type == "Windows":
            data["fan_control_note"] = (
                "HP Victus fan control is vendor-managed. Use OMEN Gaming Hub "
                "Performance or Max Fan mode on supported models."
            )
        else:
            data["fan_control_note"] = "Fan control is hardware and BIOS dependent on this platform."

        if data["cpu_temp_c"] is None and data["gpu_temp_c"] is None:
            data["note"] = (
                "Temperatures are unavailable right now. On Windows, run LibreHardwareMonitor "
                "or OpenHardwareMonitor as administrator for the richest sensor data."
            )

        self._thermal_cache = {"time": now, "data": data}
        return data

    def hardware_snapshot(self) -> dict:
        if not psutil:
            return {"available": False, "error": "psutil not installed."}
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()
            disk_root = Path.home().anchor or "/"
            disk = psutil.disk_usage(disk_root)
            battery = psutil.sensors_battery()
            thermals = self.thermal_snapshot()
            return {
                "available": True,
                "cpu_percent": cpu,
                "ram": ram,
                "disk": disk,
                "battery": battery,
                "thermals": thermals,
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    # ── Hardware ─────────────────────────────────────────────
    def hardware_report(self) -> str:
        if not psutil:
            return "psutil not installed — hardware info unavailable."
        try:
            cpu  = psutil.cpu_percent(interval=1)
            ram  = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            bat  = psutil.sensors_battery()
            ru   = ram.used  / 1024**3
            rt   = ram.total / 1024**3
            du   = disk.used  / 1024**3
            dt   = disk.total / 1024**3
            bat_s = f"{bat.percent:.0f}% ({'charging' if bat.power_plugged else 'on battery'})" if bat else "N/A"
            return (f"CPU at {cpu}%, RAM {ru:.1f}/{rt:.1f} GB ({ram.percent}%), "
                    f"Disk {du:.0f}/{dt:.0f} GB ({disk.percent}%), Battery: {bat_s}.")
        except Exception as e:
            return f"Hardware check error: {e}"

    def network_info(self) -> str:
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            pub_ip   = "unavailable"
            if requests:
                try:
                    pub_ip = requests.get("https://api.ipify.org", timeout=3).text
                except:
                    pass
            net = psutil.net_io_counters() if psutil else None
            net_s = f", {net.bytes_sent/1024**2:.1f} MB sent, {net.bytes_recv/1024**2:.1f} MB received" if net else ""
            return f"Hostname: {hostname}, Local IP: {local_ip}, Public IP: {pub_ip}{net_s}."
        except Exception as e:
            return f"Network info error: {e}"

    def top_processes(self) -> str:
        if not psutil:
            return "psutil not installed."
        procs = sorted(psutil.process_iter(["name","cpu_percent","memory_percent"]),
                       key=lambda p: p.info["cpu_percent"], reverse=True)[:5]
        result = []
        for p in procs:
            if p.info["cpu_percent"] > 0:
                result.append(f"{p.info['name']} (CPU:{p.info['cpu_percent']}%, "
                               f"RAM:{p.info['memory_percent']:.1f}%)")
        return "Top processes: " + ", ".join(result) if result else "System is idle."

    # ── App Launcher ─────────────────────────────────────────
    def open_app(self, name: str) -> str:
        n = name.lower().strip()

        # ── Windows APP_MAP — all apps from Prashant's HP Victus laptop ──
        APP_MAP = {
            # ── Browsers ──────────────────────────────────────────────
            "chrome":               ("google-chrome",         "start chrome",                        "open -a 'Google Chrome'"),
            "google chrome":        ("google-chrome",         "start chrome",                        "open -a 'Google Chrome'"),
            "edge":                 ("microsoft-edge",        "start msedge",                        "open -a 'Microsoft Edge'"),
            "microsoft edge":       ("microsoft-edge",        "start msedge",                        "open -a 'Microsoft Edge'"),
            "firefox":              ("firefox",               "start firefox",                       "open -a Firefox"),

            # ── Code / Dev ────────────────────────────────────────────
            "vscode":               ("code",                  "code",                                "open -a 'Visual Studio Code'"),
            "vs code":              ("code",                  "code",                                "open -a 'Visual Studio Code'"),
            "visual studio code":   ("code",                  "code",                                "open -a 'Visual Studio Code'"),
            "android studio":       ("studio",                "start androidstudio",                 "open -a 'Android Studio'"),
            "terminal":             ("gnome-terminal",        "wt",                                  "open -a Terminal"),
            "windows terminal":     ("gnome-terminal",        "wt",                                  "open -a Terminal"),
            "cmd":                  ("bash",                  "start cmd",                           "open -a Terminal"),
            "powershell":           ("bash",                  "start powershell",                    "open -a Terminal"),
            "python":               ("python3",               "python",                              "python3"),
            "virtualbox":           ("virtualbox",            "start virtualbox",                    "open -a VirtualBox"),
            "oracle virtualbox":    ("virtualbox",            "start virtualbox",                    "open -a VirtualBox"),
            "bluestacks":           ("bluestacks",            "start bluestacks",                    "open -a BlueStacks"),

            # ── Microsoft Office ──────────────────────────────────────
            "word":                 ("libreoffice --writer",  "start winword",                       "open -a 'Microsoft Word'"),
            "excel":                ("libreoffice --calc",    "start excel",                         "open -a 'Microsoft Excel'"),
            "powerpoint":           ("libreoffice --impress", "start powerpnt",                      "open -a 'Microsoft PowerPoint'"),
            "onenote":              ("libreoffice",           "start onenote",                       "open -a 'Microsoft OneNote'"),
            "microsoft teams":      ("teams",                 "start teams",                         "open -a 'Microsoft Teams'"),
            "teams":                ("teams",                 "start teams",                         "open -a 'Microsoft Teams'"),
            "outlook":              ("thunderbird",           "start outlook",                       "open -a Outlook"),
            "microsoft to do":      ("",                      "start ms-todo:",                      ""),
            "to do":                ("",                      "start ms-todo:",                      ""),
            "sticky notes":         ("",                      "start stikynot",                      ""),
            "clipchamp":            ("",                      "start clipchamp:",                    ""),
            "power automate":       ("",                      "start ms-powerautomate:",             ""),
            "copilot":              ("",                      "start microsoft-edge:https://copilot.microsoft.com",""),
            "microsoft copilot":    ("",                      "start microsoft-edge:https://copilot.microsoft.com",""),

            # ── Media & Entertainment ─────────────────────────────────
            "spotify":              ("spotify",               "start spotify",                       "open -a Spotify"),
            "vlc":                  ("vlc",                   "start vlc",                           "open -a VLC"),
            "vlc media player":     ("vlc",                   "start vlc",                           "open -a VLC"),
            "media player":         ("",                      "start wmplayer",                      "open -a 'Windows Media Player'"),
            "windows media player":  ("",                     "start wmplayer",                      ""),
            "sound recorder":       ("",                      "start ms-soundrecorder:",             ""),
            "xbox":                 ("",                      "start xbox:",                         ""),
            "roblox":               ("",                      "start roblox:",                       ""),
            "mech arena":           ("",                      "start mechArena:",                    ""),
            "google play games":    ("",                      "start com.google.android.gamespcapp:",""),
            "solitaire":            ("",                      "start xboxliveapp-9007:",             ""),

            # ── Communication ─────────────────────────────────────────
            "whatsapp":             ("whatsapp",              "start whatsapp:",                     "open -a WhatsApp"),
            "telegram":             ("telegram",              "start telegram",                      "open -a Telegram"),
            "discord":              ("discord",               "start discord",                       "open -a Discord"),

            # ── AI Apps ───────────────────────────────────────────────
            "chatgpt":              ("",                      "start microsoft-edge:https://chat.openai.com","open -a ChatGPT"),
            "claude":               ("",                      "start microsoft-edge:https://claude.ai","open -a Claude"),
            "codex":                ("",                      "start microsoft-edge:https://platform.openai.com",""),
            "bing":                 ("",                      "start microsoft-edge:https://bing.com",""),

            # ── System Tools ──────────────────────────────────────────
            "calculator":           ("gnome-calculator",      "calc",                                "open -a Calculator"),
            "paint":                ("gimp",                  "mspaint",                             "open -a GIMP"),
            "snipping tool":        ("",                      "start snippingtool",                  ""),
            "snip":                 ("",                      "start snippingtool",                  ""),
            "task manager":         ("gnome-system-monitor",  "taskmgr",                             "open -a 'Activity Monitor'"),
            "settings":             ("gnome-control-center",  "start ms-settings:",                  "open -a 'System Preferences'"),
            "file explorer":        ("nautilus",              "explorer",                            "open ."),
            "explorer":             ("nautilus",              "explorer",                            "open ."),
            "file manager":         ("nautilus",              "explorer",                            "open ."),
            "camera":               ("cheese",                "start microsoft.windows.camera:",     "open -a Photo Booth"),
            "photos":               ("eog",                   "start ms-photos:",                    "open -a Photos"),
            "windows clock":        ("",                      "start ms-clock:",                     ""),
            "clock":                ("",                      "start ms-clock:",                     ""),
            "weather":              ("",                      "start bingweather:",                  ""),
            "windows weather":      ("",                      "start bingweather:",                  ""),
            "quick assist":         ("",                      "start quickassist:",                  ""),
            "remote desktop":       ("",                      "start mstsc",                         ""),
            "speedtest":            ("",                      "start microsoft-edge:https://speedtest.net",""),
            "onedrive":             ("",                      "start onedrive",                      ""),
            "microsoft bing":       ("",                      "start microsoft-edge:https://bing.com",""),

            # ── HP Laptop Specific ────────────────────────────────────
            "omen gaming hub":      ("",                      "start omen gaming hub",               ""),
            "omen hub":             ("",                      "start omen gaming hub",               ""),
            "hp support":           ("",                      "start HPSupportAssistant",            ""),
            "hp support assistant": ("",                      "start HPSupportAssistant",            ""),
            "hp smart":             ("",                      "start HPSmart:",                      ""),
            "hp diagnostics":       ("",                      "start HPPCHardwareDiagnosticsWindows:",""),
            "intel graphics":       ("",                      "start igfxEM",                        ""),

            # ── Trading / Finance ─────────────────────────────────────
            "tradingview":          ("",                      "start microsoft-edge:https://tradingview.com",""),

            # ── Productivity ──────────────────────────────────────────
            "notepad":              ("gedit",                 "notepad",                             "open -a TextEdit"),
            "quick share":          ("",                      "start ms-settings-connectabledevices:",""),
        }

        WEB_MAP = {
            # ── Core ──────────────────────────────────────────────────
            "youtube":          "https://youtube.com",
            "gmail":            "https://mail.google.com",
            "google":           "https://google.com",
            "github":           "https://github.com",
            "chatgpt":          "https://chat.openai.com",
            "claude ai":        "https://claude.ai",
            "netflix":          "https://netflix.com",
            "twitter":          "https://twitter.com",
            "x.com":            "https://twitter.com",
            "instagram":        "https://instagram.com",
            "linkedin":         "https://linkedin.com",
            "facebook":         "https://facebook.com",
            "reddit":           "https://reddit.com",
            "pinterest":        "https://pinterest.com",
            # ── Study / JEE ──────────────────────────────────────────
            "jeemains":         "https://jeemain.nta.nic.in",
            "khan academy":     "https://khanacademy.org",
            "unacademy":        "https://unacademy.com",
            "physics wallah":   "https://pw.live",
            "pw":               "https://pw.live",
            "neet":             "https://neet.nta.nic.in",
            # ── Tools ────────────────────────────────────────────────
            "tradingview web":  "https://tradingview.com",
            "speedtest web":    "https://speedtest.net",
            "bing search":      "https://bing.com",
            "openrouter":       "https://openrouter.ai",
            "groq":             "https://console.groq.com",
            "google calendar":  "https://calendar.google.com",
            "google drive":     "https://drive.google.com",
            "google docs":      "https://docs.google.com",
            "google sheets":    "https://sheets.google.com",
            "google meet":      "https://meet.google.com",
            "notion":           "https://notion.so",
            "vercel":           "https://vercel.com",
            "stackoverflow":    "https://stackoverflow.com",
            "pypi":             "https://pypi.org",
        }

        # Check custom apps
        for key, path in self.custom.items():
            if key.lower() in n or n in key.lower():
                try:
                    subprocess.Popen(path, shell=True)
                    return f"Opening {key}."
                except:
                    return f"Failed to open {key}."

        # Web shortcuts
        for key, url in WEB_MAP.items():
            if key in n:
                webbrowser.open(url)
                return f"Opening {key} in your browser."

        # Desktop apps
        for key, cmds in APP_MAP.items():
            if key in n or n in key:
                linux_cmd, win_cmd, mac_cmd = cmds
                cmd = {"Linux": linux_cmd, "Windows": win_cmd, "Darwin": mac_cmd}.get(self.os_type, linux_cmd)
                try:
                    subprocess.Popen(cmd, shell=True)
                    return f"Opening {key}."
                except Exception as e:
                    return f"Failed to open {key}: {e}"

        # Fallback — try running directly
        try:
            subprocess.Popen(name, shell=True)
            return f"Attempting to launch {name}."
        except:
            return f"I couldn't find '{name}'. Add it to custom_apps in your config."

    # ── File Operations ───────────────────────────────────────
    def search_files(self, query: str, path: str = None) -> str:
        search_path = str(self._resolve_storage_path(path)) if path else str(self._default_storage_root())
        results = []
        try:
            for root, dirs, files in os.walk(search_path):
                dirs[:] = [d for d in dirs if not d.startswith(".")
                           and d not in ("AppData","node_modules","__pycache__",".git","Windows")]
                for f in files:
                    if query.lower() in f.lower():
                        results.append(os.path.join(root, f))
                    if len(results) >= 5:
                        break
                if len(results) >= 5:
                    break
        except PermissionError:
            pass
        return ("Found: " + " | ".join(results)) if results else f"No files matching '{query}'."

    def open_file(self, path: str) -> str:
        try:
            target = self._find_existing_path(path)
            if target is None or not target.exists():
                return f"I could not find '{path}' inside your allowed storage roots."
            if not self._is_allowed_storage_path(target):
                return f"Access denied for {target}."
            if self.os_type == "Windows":
                os.startfile(str(target))
            elif self.os_type == "Darwin":
                subprocess.Popen(["open", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target)])
            return f"Opening {target}."
        except Exception as e:
            return f"Cannot open file: {e}"

    def create_folder(self, path: str) -> str:
        try:
            target = self._resolve_storage_path(path)
            if not self._is_allowed_storage_path(target):
                return f"Access denied for {target}."
            target.mkdir(parents=True, exist_ok=True)
            return f"Folder ready at {target}."
        except Exception as e:
            return f"Cannot create folder: {e}"

    def create_file(self, path: str, content: str = "") -> str:
        try:
            target = self._resolve_storage_path(path)
            if not self._is_allowed_storage_path(target):
                return f"Access denied for {target}."
            target.parent.mkdir(parents=True, exist_ok=True)
            if content and target.suffix.lower() not in IMAGE_FILE_EXTENSIONS:
                with open(target, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                target.touch(exist_ok=True)
            return f"File ready at {target}."
        except Exception as e:
            return f"Cannot create file: {e}"

    def list_desktop(self) -> str:
        desktop = Path.home() / "Desktop"
        if not desktop.exists():
            desktop = Path.home()
        try:
            items = os.listdir(desktop)[:10]
            return f"Desktop contains: {', '.join(items)}."
        except:
            return "Cannot read desktop."

    # ── Volume / Screen ───────────────────────────────────────
    def set_volume(self, level: int) -> str:
        level = max(0, min(100, level))
        try:
            if self.os_type == "Windows":
                # PowerShell method (no nircmd needed)
                script = (
                    f"$obj = New-Object -ComObject WScript.Shell;"
                    f"1..50 | %{{ $obj.SendKeys([char]174) }};"  # mute first
                    f"$vol = [math]::Round({level}/2);"
                    f"1..$vol | %{{ $obj.SendKeys([char]175) }}"
                )
                subprocess.run(["powershell","-c",script], capture_output=True)
            elif self.os_type == "Darwin":
                subprocess.run(f"osascript -e 'set volume output volume {level}'", shell=True)
            else:
                subprocess.run(f"amixer sset Master {level}%", shell=True)
            return f"Volume set to {level}%."
        except Exception as e:
            return f"Volume change failed: {e}"

    def take_screenshot(self) -> str:
        if not pyautogui:
            return "pyautogui not installed. Run: pip install pyautogui"
        try:
            fname = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            path  = str(Path.home() / "Pictures" / fname)
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            pyautogui.screenshot(path)
            return f"Screenshot saved: {path}"
        except Exception as e:
            return f"Screenshot failed: {e}"

    # ── Power ─────────────────────────────────────────────────
    def shutdown(self, delay=30) -> str:
        if self.os_type == "Windows":
            subprocess.run(f"shutdown /s /t {delay}", shell=True)
        else:
            subprocess.run("shutdown -h +1", shell=True)
        return f"Shutdown scheduled in {delay} seconds."

    def restart(self) -> str:
        if self.os_type == "Windows":
            subprocess.run("shutdown /r /t 30", shell=True)
        else:
            subprocess.run("shutdown -r +1", shell=True)
        return "Restarting in 30 seconds."

    def lock_screen(self) -> str:
        if self.os_type == "Windows":
            subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
        elif self.os_type == "Darwin":
            subprocess.run("pmset displaysleepnow", shell=True)
        else:
            subprocess.run("xdg-screensaver lock", shell=True)
        return "Screen locked."

    def get_clipboard(self) -> str:
        if pyperclip:
            return f"Clipboard contains: {pyperclip.paste()}"
        return "pyperclip not installed."


def _system_hardware_report(self) -> str:
    snapshot = self.hardware_snapshot()
    if not snapshot.get("available"):
        return f"Hardware check error: {snapshot.get('error', 'unavailable')}"

    cpu = snapshot["cpu_percent"]
    ram = snapshot["ram"]
    disk = snapshot["disk"]
    bat = snapshot["battery"]
    thermals = snapshot["thermals"]

    ru = ram.used / 1024**3
    rt = ram.total / 1024**3
    du = disk.used / 1024**3
    dt = disk.total / 1024**3
    bat_s = f"{bat.percent:.0f}% ({'charging' if bat.power_plugged else 'on battery'})" if bat else "N/A"

    extras = []
    if thermals.get("cpu_temp_c") is not None:
        extras.append(f"CPU temp {thermals['cpu_temp_c']:.0f}°C")
    if thermals.get("gpu_temp_c") is not None:
        extras.append(f"GPU temp {thermals['gpu_temp_c']:.0f}°C")
    if thermals.get("fans"):
        extras.append("Fans " + ", ".join(f"{fan['name']} {fan['rpm']} RPM" for fan in thermals["fans"][:2]))
    elif thermals.get("gpu_fan_percent") is not None:
        extras.append(f"GPU fan {thermals['gpu_fan_percent']:.0f}%")

    report = (
        f"CPU at {cpu:.0f}%, RAM {ru:.1f}/{rt:.1f} GB ({ram.percent}%), "
        f"Disk {du:.0f}/{dt:.0f} GB ({disk.percent}%), Battery: {bat_s}."
    )
    if extras:
        report += " " + " | ".join(extras) + "."
    return report.replace("..", ".")


def _system_thermal_report(self) -> str:
    thermals = self.thermal_snapshot(max_age=0.0)
    parts = []
    if thermals.get("cpu_temp_c") is not None:
        parts.append(f"CPU {thermals['cpu_temp_c']:.0f}°C")
    if thermals.get("gpu_temp_c") is not None:
        label = thermals.get("gpu_name") or "GPU"
        parts.append(f"{label} {thermals['gpu_temp_c']:.0f}°C")
    if thermals.get("fans"):
        parts.append(", ".join(f"{fan['name']} {fan['rpm']} RPM" for fan in thermals["fans"]))
    elif thermals.get("gpu_fan_percent") is not None:
        parts.append(f"GPU fan {thermals['gpu_fan_percent']:.0f}%")
    if thermals.get("source"):
        parts.append(f"source {thermals['source']}")
    if thermals.get("note"):
        parts.append(thermals["note"])
    if not parts:
        return "Thermal telemetry is unavailable right now."
    return ("Thermals: " + " | ".join(parts) + ".").replace("..", ".")


def _system_open_hp_thermal_controls(self) -> str:
    if self.os_type != "Windows":
        return "HP thermal control helper is only available on Windows."

    script = (
        "$app = Get-StartApps | Where-Object { $_.Name -match 'OMEN|Gaming Hub|Victus' } | "
        "Select-Object -First 1; "
        "if ($app) { Start-Process explorer.exe ('shell:AppsFolder\\' + $app.AppID); exit 0 } "
        "exit 1"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=6,
        )
        if result.returncode == 0:
            return (
                "Opening HP OMEN Gaming Hub. On supported Victus models, switch to "
                "Performance or Max Fan mode to increase cooling."
            )
    except Exception:
        pass

    return (
        "I could not launch OMEN Gaming Hub automatically. Open it manually and use "
        "Performance, Auto, or Max Fan mode if your HP Victus model supports it."
    )


SystemModule.hardware_report = _system_hardware_report
SystemModule.thermal_report = _system_thermal_report
SystemModule.open_hp_thermal_controls = _system_open_hp_thermal_controls

# ═══════════════════════════════════════════════════════════════
#  EMAIL MODULE
# ═══════════════════════════════════════════════════════════════
class EmailModule:
    def __init__(self, cfg: dict):
        self.email    = cfg.get("email","")
        self.password = cfg.get("email_password","")
        self.imap     = cfg.get("imap_server","imap.gmail.com")
        self.smtp     = cfg.get("smtp_server","smtp.gmail.com")
        self.port     = cfg.get("smtp_port", 587)
        self.enabled  = bool(self.email and self.password)

    def _decode(self, h) -> str:
        parts  = decode_header(h or "")
        result = []
        for part, enc in parts:
            if isinstance(part, bytes):
                result.append(part.decode(enc or "utf-8", errors="ignore"))
            else:
                result.append(str(part))
        return " ".join(result)

    def check_inbox(self, count=5) -> str:
        if not self.enabled:
            return "Email not configured in jarvis_config.json."
        try:
            mail = imaplib.IMAP4_SSL(self.imap)
            mail.login(self.email, self.password)
            mail.select("inbox")
            _, data = mail.search(None, "UNSEEN")
            ids = data[0].split()
            if not ids:
                mail.logout()
                return "Your inbox is clear — no unread messages."
            summaries = []
            for uid in reversed(ids[-count:]):
                _, msg_data = mail.fetch(uid, "(RFC822)")
                msg     = email_lib.message_from_bytes(msg_data[0][1])
                sender  = self._decode(msg.get("From","?")).split("<")[0].strip().strip('"')
                subject = self._decode(msg.get("Subject","No subject"))
                summaries.append(f"From {sender}: '{subject}'")
            mail.logout()
            return (f"You have {len(ids)} unread email{'s' if len(ids)>1 else ''}. "
                    + " | ".join(summaries[:3]))
        except Exception as e:
            return f"Email error: {e}"

    def send_email(self, to: str, subject: str, body: str) -> str:
        if not self.enabled:
            return "Email not configured."
        try:
            msg              = MIMEMultipart()
            msg["From"]      = self.email
            msg["To"]        = to
            msg["Subject"]   = subject
            msg.attach(MIMEText(body, "plain"))
            srv = smtplib.SMTP(self.smtp, self.port)
            srv.starttls()
            srv.login(self.email, self.password)
            srv.send_message(msg)
            srv.quit()
            return f"Email sent to {to}."
        except Exception as e:
            return f"Send failed: {e}"

# ═══════════════════════════════════════════════════════════════
#  WEATHER MODULE
# ═══════════════════════════════════════════════════════════════
class WeatherModule:
    def __init__(self, cfg: dict):
        self.key      = cfg.get("openweather_api_key","")
        self.location = cfg.get("location","Bihar, India")
        self.enabled  = bool(self.key)

    def current(self, city: str = None) -> str:
        city = city or self.location
        if not self.enabled:
            return "Weather API key not set. Get a free one at openweathermap.org."
        if not requests:
            return "requests package not installed."
        try:
            r = requests.get("https://api.openweathermap.org/data/2.5/weather",
                             params={"q":city,"appid":self.key,"units":"metric"}, timeout=5)
            d = r.json()
            if r.status_code != 200:
                return f"Weather unavailable: {d.get('message','error')}"
            return (f"{city}: {d['main']['temp']:.0f}°C, {d['weather'][0]['description']}, "
                    f"feels like {d['main']['feels_like']:.0f}°C, "
                    f"humidity {d['main']['humidity']}%.")
        except Exception as e:
            return f"Weather fetch failed: {e}"

# ═══════════════════════════════════════════════════════════════
#  NEWS MODULE
# ═══════════════════════════════════════════════════════════════
class NewsModule:
    def __init__(self, cfg: dict):
        self.key     = cfg.get("news_api_key","")
        self.enabled = bool(self.key)

    def headlines(self, query: str = None, country: str = "in") -> str:
        if not requests:
            return "requests package not installed."

        # Prefer NewsAPI when key is set, otherwise fall back to Google News RSS (no key).
        headers = {
            "User-Agent": "JARVIS/2.0 (+local assistant)",
            "Accept": "application/json, text/xml, application/xml;q=0.9, */*;q=0.8",
        }
        if self.enabled and self.key:
            try:
                params = {"apiKey": self.key, "country": country, "pageSize": 5}
                if query:
                    params["q"] = query
                r = requests.get("https://newsapi.org/v2/top-headlines", params=params, headers=headers, timeout=6)
                payload = r.json() if r.headers.get("content-type", "").lower().startswith("application/json") else {}
                if r.status_code != 200:
                    msg = ""
                    try:
                        msg = str(payload.get("message", "")).strip()
                    except Exception:
                        msg = ""
                    raise RuntimeError(f"NewsAPI HTTP {r.status_code}" + (f": {msg}" if msg else ""))
                articles = (payload or {}).get("articles", [])[:4]
                if not articles:
                    return "No headlines found."
                return "Headlines: " + " | ".join(a.get("title", "").strip() for a in articles if a.get("title")) + "."
            except Exception as e:
                # Fall through to RSS as a recovery path.
                last_err = str(e)
        else:
            last_err = ""

        try:
            import xml.etree.ElementTree as ET
            from html import unescape

            # Google News RSS supports query via "search".
            if query:
                url = "https://news.google.com/rss/search"
                params = {"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
            else:
                url = "https://news.google.com/rss"
                params = {"hl": "en-IN", "gl": "IN", "ceid": "IN:en"}

            r = requests.get(url, params=params, headers=headers, timeout=8)
            xml = r.text or ""
            root = ET.fromstring(xml)
            titles = []
            for item in root.findall(".//item"):
                t = item.findtext("title") or ""
                t = unescape(t).strip()
                if t:
                    # Google News titles often include " - Source". Keep the headline part.
                    if " - " in t:
                        t = t.split(" - ", 1)[0].strip()
                    titles.append(t)
                if len(titles) >= 4:
                    break
            if not titles:
                return "No headlines found."
            return "Headlines: " + " | ".join(titles) + "."
        except Exception as e:
            extra = f" (NewsAPI error: {last_err})" if last_err else ""
            return f"News fetch failed: {e}{extra}"

# ═══════════════════════════════════════════════════════════════
#  LOCATION MODULE — IP geolocation + GPS via browser API
# ═══════════════════════════════════════════════════════════════
class LocationModule:
    def __init__(self, cfg: dict):
        self.cfg          = cfg
        self.google_maps_api_key = str(cfg.get("google_maps_api_key", "")).strip()
        self.manual_label = str(cfg.get("location_label") or cfg.get("location") or "").strip()
        self.manual_lat   = self._coerce_float(cfg.get("location_lat"))
        self.manual_lon   = self._coerce_float(cfg.get("location_lon"))
        self.cached: dict = {}
        self._lock        = threading.Lock()
        if self.manual_lat is not None and self.manual_lon is not None:
            self.cached = {
                "city": self.manual_label,
                "region": "",
                "country": "",
                "lat": self.manual_lat,
                "lon": self.manual_lon,
                "isp": "manual override",
                "ip": "",
            }
        self._refresh()  # background fetch on init

    def _coerce_float(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _refresh(self):
        if self.manual_lat is not None and self.manual_lon is not None:
            return
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        """Fetch location via IP geolocation — free, no API key needed."""
        if not requests:
            return
        try:
            # ip-api.com — free, 45 requests/min, no key required
            r = requests.get("http://ip-api.com/json/?fields=status,city,regionName,country,lat,lon,isp,query",
                             timeout=5)
            data = r.json()
            if data.get("status") == "success":
                with self._lock:
                    self.cached = {
                        "city":    data.get("city", ""),
                        "region":  data.get("regionName", ""),
                        "country": data.get("country", ""),
                        "lat":     data.get("lat", 0.0),
                        "lon":     data.get("lon", 0.0),
                        "isp":     data.get("isp", ""),
                        "ip":      data.get("query", ""),
                    }
        except Exception as e:
            print(f"[Location] Fetch failed: {e}")

    def get(self) -> dict:
        with self._lock:
            return dict(self.cached)

    def get_str(self) -> str:
        d = self.get()
        if self.manual_label and self.manual_lat is not None and self.manual_lon is not None:
            return self.manual_label
        if not d:
            return self.cfg.get("location", "Location unavailable")
        return f"{d.get('city','')}, {d.get('region','')}, {d.get('country','')} (IP: {d.get('ip','')})"

    def get_coords(self) -> tuple[float, float] | None:
        d = self.get()
        if d and d.get("lat") and d.get("lon"):
            return float(d["lat"]), float(d["lon"])
        return None

    def get_map_url(self, zoom: int = 13) -> str:
        """Returns a Google Maps URL centered on current location."""
        coords = self.get_coords()
        if coords:
            lat, lon = coords
            return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
        query = requests.utils.quote(self.get_str()) if requests else self.get_str().replace(" ", "+")
        return f"https://www.google.com/maps/search/?api=1&query={query}"

    def get_static_map_url(self, width=300, height=160, zoom=12) -> str:
        """Returns a Google Maps static preview URL when an API key is configured."""
        coords = self.get_coords()
        if coords and self.google_maps_api_key:
            lat, lon = coords
            marker = requests.utils.quote(f"color:red|label:J|{lat},{lon}") if requests else f"color:red|label:J|{lat},{lon}"
            return (
                "https://maps.googleapis.com/maps/api/staticmap"
                f"?center={lat},{lon}&zoom={zoom}&size={width}x{height}"
                f"&maptype=roadmap&markers={marker}&key={self.google_maps_api_key}"
            )
        return ""

    def refresh(self) -> str:
        if self.manual_lat is not None and self.manual_lon is not None:
            return "Location is locked to your configured exact coordinates."
        self._refresh()
        return "Location refresh initiated."

    def open_in_browser(self):
        webbrowser.open(self.get_map_url())

# ═══════════════════════════════════════════════════════════════
#  NOTES MODULE
# ═══════════════════════════════════════════════════════════════
class NotesModule:
    def __init__(self):
        self.file  = NOTES_FILE
        self.notes = self._load()

    def _load(self) -> list:
        if self.file.exists():
            with open(self.file) as f:
                return json.load(f)
        return []

    def _save(self):
        with open(self.file,"w") as f:
            json.dump(self.notes, f, indent=2)

    def add(self, content: str) -> str:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.notes.append({"text": content, "time": ts})
        self._save()
        return f"Note saved: '{content}'."

    def read(self) -> str:
        if not self.notes:
            return "No notes saved."
        last5 = self.notes[-5:]
        return "Notes: " + " | ".join(n["text"] for n in last5) + "."

    def clear(self) -> str:
        self.notes.clear()
        self._save()
        return "All notes cleared."

    def set_reminder(self, text: str, minutes: int, callback) -> str:
        def _fire():
            time.sleep(minutes * 60)
            callback(f"Reminder: {text}")
        threading.Thread(target=_fire, daemon=True).start()
        return f"Reminder set for {minutes} minute{'s' if minutes>1 else ''}: '{text}'."

# ═══════════════════════════════════════════════════════════════
#  CALENDAR MODULE
# ═══════════════════════════════════════════════════════════════
class CalendarModule:
    def __init__(self):
        self.file   = EVENTS_FILE
        self.events = self._load()

    def _load(self) -> list:
        if self.file.exists():
            with open(self.file) as f:
                return json.load(f)
        return []

    def _save(self):
        with open(self.file,"w") as f:
            json.dump(self.events, f, indent=2)

    def today(self) -> str:
        td = datetime.date.today().isoformat()
        ev = [e for e in self.events if e.get("date","") == td]
        if not ev:
            return "No events scheduled for today."
        return "Today: " + " | ".join(f"{e['time']} — {e['title']}" for e in ev) + "."

    def upcoming(self, days=7) -> str:
        start = datetime.date.today()
        end   = start + datetime.timedelta(days=days)
        ev    = [e for e in self.events
                 if start.isoformat() <= e.get("date","") <= end.isoformat()]
        if not ev:
            return f"No events in the next {days} days."
        return "Upcoming: " + " | ".join(f"{e['date']} {e['time']} {e['title']}" for e in ev[:5]) + "."

    def add(self, title, date, time_str="00:00") -> str:
        self.events.append({"title":title,"date":date,"time":time_str})
        self._save()
        return f"Event '{title}' added for {date} at {time_str}."

# ═══════════════════════════════════════════════════════════════
#  INTENT CLASSIFIER
# ═══════════════════════════════════════════════════════════════
class Intent:
    MAP = {
        "open_app":       ["open","launch","start","run"],
        "hardware":       ["cpu","ram","memory","disk","battery","hardware","system status","performance"],
        "thermal_status": ["cpu temp","cpu temps","cpu temperature","gpu temp","gpu temps","gpu temperature","thermal status","thermal report","system temperature","temperatures","fan rpm","fan speed","cooling status"],
        "fan_control":    ["speed up fan","increase fan","boost fan","cooler fan","fan mode","cooling mode","max fan","open omen","omen gaming hub","victus cooling","victus fan"],
        "network":        ["network","ip","internet","wifi","connection"],
        "email_check":    ["check email","emails","inbox","unread mail","any mail","new mail"],
        "send_email":     ["send email","send mail","email to","compose","write email"],
        "calendar_today": ["today's schedule","today's events","what's today","schedule today"],
        "calendar_upcoming": ["upcoming","this week","next week","my schedule"],
        "add_event":      ["add event","schedule","book meeting","create event"],
        "open_calendar":  ["open calendar","google calendar","show calendar"],
        "weather":        ["weather","temperature","raining","forecast","sunny","hot outside"],
        "note_add":       ["take a note","note that","write down","remember this","jot"],
        "note_read":      ["read notes","my notes","show notes","what notes"],
        "note_clear":     ["clear notes","delete notes"],
        "reminder":       ["remind me","set reminder","reminder in","alert me"],
        "news":           ["news","headlines","what's happening","latest news"],
        "time":           ["what time","current time","the time"],
        "date":           ["what date","today's date","what day","what's today's date"],
        "screenshot":     ["screenshot","capture screen","take screenshot"],
        "volume":         ["volume","set volume","turn up","turn down","mute"],
        "search_files":   ["find file","search file","look for file","locate file","where is file"],
        "open_file":      ["open file","open document","open folder"],
        "desktop":        ["what's on desktop","show desktop","list desktop"],
        "clipboard":      ["clipboard","what did i copy"],
        "processes":      ["running processes","top processes","what's running"],
        "camera_photo":   ["take photo","take picture","capture photo","selfie","click photo","open camera photo"],
        "camera_video":   ["record video","capture video","record clip"],
        "camera_live":    ["open camera","show camera","live camera","camera feed","camera view"],
        "camera_analyze": ["what do you see","analyze camera","describe what you see","look through camera","what's in front"],
        "camera_list":    ["list cameras","available cameras","check camera","detect camera"],
        "web_search":     ["search for","google","look up","search online","find online"],
        "shutdown":       ["shutdown","shut down","power off","turn off computer"],
        "restart":        ["restart","reboot"],
        "lock":           ["lock","lock screen","lock computer"],
        "clear_chat":     ["clear chat","reset","forget conversation","new conversation"],
        "joke":           ["joke","make me laugh","say something funny"],
        "greet":          ["hello jarvis","hi jarvis","hey jarvis","good morning","good evening","good afternoon","good night"],
        "stop":           ["exit","quit","goodbye","bye","shutdown jarvis","stop jarvis","turn off jarvis"],
    }

    @classmethod
    def classify(cls, text: str) -> str:
        lower = text.lower()
        for intent, keywords in cls.MAP.items():
            if any(kw in lower for kw in keywords):
                return intent
        return "ai_chat"

# ═══════════════════════════════════════════════════════════════
#  GREETING
# ═══════════════════════════════════════════════════════════════
class Greeter:
    def __init__(self, name: str):
        self.name = name

    def greet(self) -> str:
        h = datetime.datetime.now().hour
        period = "Good morning" if 4<=h<12 else "Good afternoon" if 12<=h<17 else "Good evening" if 17<=h<21 else "Good night"
        t = datetime.datetime.now().strftime("%I:%M %p")
        d = datetime.datetime.now().strftime("%A, %B %d")
        lines = [
            f"{period}, {self.name}. It's {t} on {d}. All systems are online and ready.",
            f"{period}, {self.name}. J.A.R.V.I.S online. {d}, {t}. How may I assist?",
            f"{period}, {self.name}. Systems initialized at {t}. Ready when you are.",
        ]
        return random.choice(lines)

    def bye(self) -> str:
        return random.choice([
            f"Going offline, {self.name}. J.A.R.V.I.S standing by.",
            f"Shutting down. Stay sharp, {self.name}.",
            f"Until next time, {self.name}.",
        ])

# ═══════════════════════════════════════════════════════════════
#  JARVIS CORE
# ═══════════════════════════════════════════════════════════════
class JARVIS:
    def __init__(self):
        banner = "═" * 60
        try:
            print("\n" + banner)
            print("  J.A.R.V.I.S v2.0 - Initializing Systems...")
            print(banner)
        except UnicodeEncodeError:
            banner = "=" * 60
            print("\n" + banner)
            print("  J.A.R.V.I.S v2.0 - Initializing Systems...")
            print(banner)

        self.cfg      = load_config()
        self.name     = self.cfg.get("user_name","Sir")
        self.voice    = VoiceEngine(self.cfg)
        self.ai       = AIBrain(self.cfg)
        self.system   = SystemModule(self.cfg)
        self.camera   = CameraModule(self.cfg)
        self.email    = EmailModule(self.cfg)
        self.weather  = WeatherModule(self.cfg)
        self.news     = NewsModule(self.cfg)
        self.location = LocationModule(self.cfg)
        self.notes    = NotesModule()
        self.calendar = CalendarModule()
        self.greeter  = Greeter(self.name)
        self.wakes    = self.cfg.get("wake_words",["jarvis","hey jarvis"])
        self._running = True
        self.text_mode = False

        try:
            print("  [OK] All systems online.\n")
        except UnicodeEncodeError:
            pass

    def boot(self):
        self.voice.speak(self.greeter.greet())
        hw = self.system.hardware_report()
        self.voice.speak(f"Quick system check: {hw}")

    # ── Main command handler ──────────────────────────────────
    def _extract_storage_path(self, text: str) -> str | None:
        source = str(text or "").strip()
        if not source:
            return None

        quoted = re.search(r'"([^"]+)"', source) or re.search(r"'([^']+)'", source)
        if quoted:
            return quoted.group(1).strip()

        drive = re.search(r"([A-Za-z]:\\.*?)(?=\s+\bwith content\b|$)", source, re.I)
        if drive:
            return drive.group(1).strip().rstrip(" .")
        return None

    def _handle_storage_command(self, text: str) -> str | None:
        lower = text.lower().strip()
        explicit_path = self._extract_storage_path(text)

        if explicit_path and lower.startswith(("open ", "show ", "launch ")):
            return self.system.open_file(explicit_path)

        if re.search(r"\b(?:create|make|new)\s+folder\b", lower):
            folder_path = explicit_path or re.split(r"\b(?:create|make|new)\s+folder\b", text, maxsplit=1, flags=re.I)[-1].strip()
            return self.system.create_folder(folder_path) if folder_path else "Tell me which folder path to create."

        if re.search(r"\b(?:create|make|new)\s+file\b", lower):
            file_path = explicit_path or re.split(r"\b(?:create|make|new)\s+file\b", text, maxsplit=1, flags=re.I)[-1].strip()
            content = ""
            if " with content " in lower:
                parts = re.split(r"\bwith content\b", text, maxsplit=1, flags=re.I)
                file_path = explicit_path or parts[0].split("file", 1)[-1].strip()
                content = parts[1].strip() if len(parts) > 1 else ""
            return self.system.create_file(file_path, content) if file_path else "Tell me which file path to create."

        if re.search(r"\bopen (?:file|folder|document)\b", lower):
            path = explicit_path or re.split(r"\bopen (?:file|folder|document)\b", text, maxsplit=1, flags=re.I)[-1].strip()
            return self.system.open_file(path) if path else "Tell me which path to open."

        if re.search(r"\b(?:find|search|locate|where is)\s+file\b", lower):
            path = explicit_path
            query = re.split(r"\b(?:find|search|look for|locate|where is)\s+file\b", text, maxsplit=1, flags=re.I)[-1].strip()
            if path and query.endswith(path):
                query = query[:-len(path)].strip()
            if " in " in query.lower():
                parts = re.split(r"\bin\b", query, maxsplit=1, flags=re.I)
                query = parts[0].strip()
                path = path or parts[1].strip()
            return self.system.search_files(query, path) if query else "Tell me which filename to search for."

        return None

    def handle(self, text: str) -> str:
        if not text or not text.strip():
            return ""

        storage_resp = self._handle_storage_command(text)
        if storage_resp:
            self.voice.speak(storage_resp)
            return storage_resp

        intent = Intent.classify(text)
        lower  = text.lower()
        resp   = ""

        # ── STOP ─────────────────────────────────────
        if intent == "stop":
            resp = self.greeter.bye()
            self.voice.speak(resp)
            self._running = False
            return resp

        # ── GREET ─────────────────────────────────────
        elif intent == "greet":
            resp = self.greeter.greet()

        # ── TIME / DATE ───────────────────────────────
        elif intent == "time":
            resp = f"It's {datetime.datetime.now().strftime('%I:%M %p')}, {self.name}."

        elif intent == "date":
            resp = f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}."

        # ── OPEN APP ──────────────────────────────────
        elif intent == "open_app":
            app = re.sub(r"\b(open|launch|start|run|execute)\b","",lower,flags=re.I).strip()
            resp = self.system.open_app(app or "chrome")

        # ── HARDWARE ──────────────────────────────────
        elif intent == "hardware":
            resp = self.system.hardware_report()

        elif intent == "thermal_status":
            resp = self.system.thermal_report()

        elif intent == "fan_control":
            resp = self.system.open_hp_thermal_controls()

        elif intent == "network":
            resp = self.system.network_info()

        elif intent == "processes":
            resp = self.system.top_processes()

        # ── EMAIL ─────────────────────────────────────
        elif intent == "email_check":
            self.voice.speak("Checking your inbox...")
            resp = self.email.check_inbox(5)

        elif intent == "send_email":
            self.voice.speak("To whom?")
            to = self.listen_or_type()
            self.voice.speak("Subject?")
            sub = self.listen_or_type()
            self.voice.speak("What should I say?")
            body = self.listen_or_type()
            resp = self.email.send_email(to, sub, body) if all([to,sub,body]) else "Email cancelled."

        # ── CALENDAR ──────────────────────────────────
        elif intent == "calendar_today":
            resp = self.calendar.today()

        elif intent == "calendar_upcoming":
            resp = self.calendar.upcoming()

        elif intent == "add_event":
            self.voice.speak("Event title?")
            title = self.listen_or_type()
            self.voice.speak("Date? For example, 2025-07-15.")
            date  = self.listen_or_type()
            self.voice.speak("Time?")
            tstr  = self.listen_or_type() or "00:00"
            resp  = self.calendar.add(title, date, tstr) if title and date else "Event cancelled."

        elif intent == "open_calendar":
            webbrowser.open("https://calendar.google.com")
            resp = "Opening Google Calendar."

        # ── WEATHER ───────────────────────────────────
        elif intent == "weather":
            city = None
            for prep in ["in ","for ","at "]:
                if prep in lower:
                    city = lower.split(prep,1)[-1].strip()
                    break
            resp = self.weather.current(city)

        # ── NOTES ─────────────────────────────────────
        elif intent == "note_add":
            self.voice.speak("What should I note?")
            content = self.listen_or_type()
            resp = self.notes.add(content) if content else "Note cancelled."

        elif intent == "note_read":
            resp = self.notes.read()

        elif intent == "note_clear":
            resp = self.notes.clear()

        # ── REMINDER ──────────────────────────────────
        elif intent == "reminder":
            self.voice.speak("What should I remind you about?")
            rem = self.listen_or_type()
            self.voice.speak("In how many minutes?")
            mins_str = self.listen_or_type() or "5"
            try:
                mins = int(re.search(r"\d+", mins_str).group())
            except:
                mins = 5
            resp = self.notes.set_reminder(rem, mins, lambda m: self.voice.speak(m))

        # ── NEWS ──────────────────────────────────────
        elif intent == "news":
            query = None
            for kw in ["about ","on ","regarding "]:
                if kw in lower:
                    query = lower.split(kw,1)[-1].strip()
                    break
            resp = self.news.headlines(query)

        # ── SCREENSHOT ────────────────────────────────
        elif intent == "screenshot":
            resp = self.system.take_screenshot()

        # ── VOLUME ────────────────────────────────────
        elif intent == "volume":
            nums = re.findall(r"\d+", text)
            if nums:
                resp = self.system.set_volume(int(nums[0]))
            elif "mute" in lower:
                resp = self.system.set_volume(0)
            else:
                resp = "Specify a volume level, like 'set volume to 60'."

        # ── FILE ──────────────────────────────────────
        elif intent == "search_files":
            inline_query = re.sub(r"\b(find|search|look for|locate|where is)\s+file\b", "", text, flags=re.I).strip()
            resp = self.system.search_files(inline_query) if inline_query else "Tell me which filename to search for."

        elif intent == "open_file":
            inline_path = self._extract_storage_path(text) or re.sub(r"\bopen (file|folder|document)\b", "", text, flags=re.I).strip()
            resp = self.system.open_file(inline_path) if inline_path else "Tell me which path to open."

        elif intent == "desktop":
            resp = self.system.list_desktop()

        elif intent == "clipboard":
            resp = self.system.get_clipboard()

        # ── CAMERA — PHOTO ────────────────────────────
        elif intent == "camera_photo":
            self.voice.speak("Capturing photo, hold still.")
            ok, result = self.camera.capture_photo()
            resp = f"Photo saved at {result}." if ok else result

        # ── CAMERA — VIDEO ────────────────────────────
        elif intent == "camera_video":
            nums = re.findall(r"\d+", text)
            secs = int(nums[0]) if nums else 10
            self.voice.speak(f"Recording {secs} second video.")
            ok, result = self.camera.record_video(secs)
            resp = f"Video saved at {result}." if ok else result

        # ── CAMERA — LIVE FEED ────────────────────────
        elif intent == "camera_live":
            self.voice.speak("Opening camera feed. Press Q to close.")
            threading.Thread(target=self.camera.show_live_feed, daemon=True).start()
            resp = "Camera feed opened. Press Q in the camera window to close."

        # ── CAMERA — AI ANALYSIS ──────────────────────
        elif intent == "camera_analyze":
            self.voice.speak("Taking a photo to analyze. One moment.")
            ok, path = self.camera.capture_photo()
            if ok:
                self.voice.speak("Analyzing the image...")
                question = text if len(text) > 15 else "Describe everything you see in detail."
                analysis = self.ai.analyze_image(path, question)
                resp = analysis
            else:
                resp = path  # error message

        # ── CAMERA — LIST ─────────────────────────────
        elif intent == "camera_list":
            resp = self.camera.list_cameras()

        # ── LOCATION ──────────────────────────────────
        elif intent == "location":
            loc = self.location.get_str()
            coords = self.location.get_coords()
            coord_str = f" Coordinates: {coords[0]:.4f}, {coords[1]:.4f}." if coords else ""
            if "map" in lower or "open map" in lower:
                self.location.open_in_browser()
                resp = f"Opening your location on Google Maps.{coord_str}"
            else:
                resp = f"Your current location is {loc}.{coord_str}"

        # ── POWER ─────────────────────────────────────
        elif intent == "shutdown":
            self.voice.speak(f"Are you sure you want to shut down, {self.name}? Say yes to confirm.")
            confirm = self.listen_or_type()
            resp = self.system.shutdown() if confirm and "yes" in confirm.lower() else "Shutdown cancelled."

        elif intent == "restart":
            resp = self.system.restart()

        elif intent == "lock":
            resp = self.system.lock_screen()

        # ── WEB SEARCH ────────────────────────────────
        elif intent == "web_search":
            query = re.sub(r"\b(search for|google|look up|search online|find online)\b","",text,flags=re.I).strip()
            if query:
                webbrowser.open(f"https://www.google.com/search?q={query}")
                resp = f"Searching Google for '{query}'."
            else:
                resp = "What should I search for?"

        # ── CLEAR CHAT ────────────────────────────────
        elif intent == "clear_chat":
            self.ai.reset()
            resp = f"Conversation memory cleared, {self.name}. Fresh start."

        # ── JOKE ──────────────────────────────────────
        elif intent == "joke":
            jokes = [
                f"I tried to write a joke about artificial intelligence, {self.name}, but I couldn't think of one. I'll outsource it.",
                f"Why do programmers prefer dark mode? Because light attracts bugs, {self.name}.",
                f"I would tell you a UDP joke, {self.name}, but you might not get it.",
                f"Why did the hacker break up with the internet? Too many connections, {self.name}.",
            ]
            resp = random.choice(jokes)

        # ── AI FALLBACK ───────────────────────────────
        else:
            try:
                ctx  = f"Time: {datetime.datetime.now().strftime('%A %I:%M %p')}, OS: {platform.system()}"
                resp = self.ai.chat(text, context=ctx)
            except Exception as e:
                resp = f"AI error: {e}"

        if resp:
            self.voice.speak(resp)
        return resp

    # ── Input helper ──────────────────────────────────────────
    def listen_or_type(self) -> str | None:
        if self.text_mode:
            try:
                return input("  > ").strip() or None
            except:
                return None
        result = self.voice.listen(timeout=8)
        if result is None:
            try:
                result = input("  [Type] > ").strip() or None
            except:
                pass
        return result

    # ── Run modes ─────────────────────────────────────────────
    def run_text(self):
        self.text_mode = True
        self.boot()
        print(f"\n[TEXT MODE] Type commands below. Type 'exit' to quit.\n")
        while self._running:
            try:
                cmd = input(f"[{self.name}] > ").strip()
                if cmd:
                    self.handle(cmd)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[Error] {e}")

    def run_voice(self):
        self.boot()
        self.voice.speak(f"Listening for '{self.wakes[0]}'.")
        while self._running:
            try:
                if self.voice.wait_wake_word(self.wakes):
                    self.voice.speak("Yes?")
                    cmd = self.voice.listen(timeout=8)
                    if cmd:
                        self.handle(cmd)
            except KeyboardInterrupt:
                break
            except Exception as e:
                if "PyAudio" not in str(e):
                    print(f"[Error] {e}")
                time.sleep(1)
        self.voice.speak(self.greeter.bye())

    def run_hybrid(self):
        self.boot()
        print(f"\n[INFO] Say '{self.wakes[0]}' OR just type below and press Enter.")
        print("[INFO] Press Ctrl+C to exit.\n")

        def text_thread():
            while self._running:
                try:
                    cmd = input("").strip()
                    if cmd:
                        self.handle(cmd)
                except (EOFError, KeyboardInterrupt):
                    break

        threading.Thread(target=text_thread, daemon=True).start()

        while self._running:
            try:
                if self.voice.wait_wake_word(self.wakes):
                    self.voice.speak("Yes?")
                    cmd = self.voice.listen(timeout=8)
                    if cmd:
                        self.handle(cmd)
            except KeyboardInterrupt:
                break
            except Exception as e:
                if "PyAudio" not in str(e):
                    print(f"[Error] {e}")
                time.sleep(0.5)

        self.voice.speak(self.greeter.bye())

# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="J.A.R.V.I.S v2.0")
    p.add_argument("--mode", choices=["text","voice","hybrid"], default="hybrid")
    args = p.parse_args()

    j = JARVIS()
    try:
        if   args.mode == "text":   j.run_text()
        elif args.mode == "voice":  j.run_voice()
        else:                       j.run_hybrid()
    except KeyboardInterrupt:
        print("\n[JARVIS] Shutting down gracefully...")
