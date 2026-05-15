from __future__ import annotations

import json
import os
import threading
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex

try:
    from plyer import stt, tts
    VOICE_SUPPORT = True
except ImportError:
    VOICE_SUPPORT = False

SETTINGS_FILE = "jarvis_mobile_settings.json"

class MessageBubble(BoxLayout):
    def __init__(self, text, is_user=False, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, padding=(dp(10), dp(5)), spacing=dp(10), **kwargs)
        self.is_user = is_user
        
        bg_color = get_color_from_hex("#2F2F2F") if is_user else get_color_from_hex("#212121")
        text_color = get_color_from_hex("#ECECEC")
        
        self.lbl = Label(text=text, color=text_color, size_hint_y=None, markup=True, halign="left", valign="top")
        self.lbl.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
        self.lbl.bind(texture_size=self._update_height)
        
        if is_user:
            self.add_widget(BoxLayout(size_hint_x=0.1))
            
        bubble_box = BoxLayout(size_hint_x=0.9, padding=dp(15))
        with bubble_box.canvas.before:
            Color(*bg_color)
            self.rect = RoundedRectangle(radius=[dp(15)])
        bubble_box.bind(pos=self._update_rect, size=self._update_rect)
        bubble_box.add_widget(self.lbl)
        
        self.add_widget(bubble_box)
        
        if not is_user:
            self.add_widget(BoxLayout(size_hint_x=0.1))
            
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
        
    def _update_height(self, instance, value):
        self.lbl.height = value[1]
        self.height = value[1] + dp(30)


class JarvisClient(BoxLayout):
    status = StringProperty("Ready")

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(5), padding=dp(10), **kwargs)
        
        # UI Styling Colors (Modern ChatGPT Dark Mode)
        Window.clearcolor = get_color_from_hex("#212121")
        bg_input = get_color_from_hex("#2F2F2F")
        accent = get_color_from_hex("#10A37F")
        text_color = get_color_from_hex("#ECECEC")
        
        self.settings = self.load_settings()
        
        # Title Bar
        title_bar = BoxLayout(size_hint_y=None, height=dp(50), padding=dp(5))
        title_lbl = Label(text="J.A.R.V.I.S", font_size=dp(20), bold=True, color=text_color, halign="center")
        settings_btn = Button(text="⚙", size_hint_x=None, width=dp(50), background_normal='', background_color=get_color_from_hex("#212121"), color=accent, font_size=dp(24))
        settings_btn.bind(on_press=self.toggle_settings)
        title_bar.add_widget(Label(size_hint_x=None, width=dp(50))) # Spacer
        title_bar.add_widget(title_lbl)
        title_bar.add_widget(settings_btn)
        self.add_widget(title_bar)

        # Settings Panel (Hidden by default)
        self.settings_panel = BoxLayout(orientation="vertical", size_hint_y=None, height=0, opacity=0, spacing=dp(5))
        self.api_key_input = TextInput(
            text=self.settings.get("api_key", ""),
            hint_text="OpenRouter API Key (sk-or-v1-...)", multiline=False, password=True,
            size_hint_y=None, height=dp(40), background_color=bg_input, foreground_color=text_color, cursor_color=accent
        )
        self.api_key_input.bind(text=self.save_settings)
        self.settings_panel.add_widget(self.api_key_input)
        self.add_widget(self.settings_panel)

        # Chat ScrollView
        self.chat_container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10))
        self.chat_container.bind(minimum_height=self.chat_container.setter('height'))
        
        self.scroll = ScrollView(size_hint=(1, 1), effect_cls='ScrollEffect')
        self.scroll.add_widget(self.chat_container)
        self.add_widget(self.scroll)

        # Command Input Area
        input_row = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(10), padding=dp(5))
        
        if VOICE_SUPPORT:
            self.mic_btn = Button(text="🎙", size_hint_x=None, width=dp(50), background_normal='', background_color=bg_input, color=text_color, font_size=dp(24))
            self.mic_btn.bind(on_press=lambda _btn: self.start_listening())
            input_row.add_widget(self.mic_btn)

        self.command = TextInput(
            hint_text="Message JARVIS...", multiline=False,
            background_color=bg_input, foreground_color=text_color, cursor_color=accent,
            padding=[dp(15), dp(15), dp(15), dp(15)]
        )
        self.command.bind(on_text_validate=lambda _btn: self.send_command())
        input_row.add_widget(self.command)

        self.send = Button(text="↑", size_hint_x=None, width=dp(50), background_normal='', background_color=accent, color=get_color_from_hex("#FFFFFF"), font_size=dp(24), bold=True)
        self.send.bind(on_press=lambda _btn: self.send_command())
        input_row.add_widget(self.send)

        self.add_widget(input_row)
        
        # Conversation history
        self.history = [{"role": "system", "content": "You are J.A.R.V.I.S, an advanced AI assistant. Keep answers concise."}]
        
        # Welcome message
        self.add_message("Hello! I am JARVIS. How can I help you today?", is_user=False)
        
    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    return json.load(f)
            except:
                pass
        return {"api_key": ""}
        
    def save_settings(self, instance, value):
        self.settings["api_key"] = value
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f)
        except Exception as e:
            print("Failed to save settings", e)

    def toggle_settings(self, instance):
        if self.settings_panel.height == 0:
            self.settings_panel.height = dp(40)
            self.settings_panel.opacity = 1
        else:
            self.settings_panel.height = 0
            self.settings_panel.opacity = 0

    def add_message(self, text, is_user=False):
        bubble = MessageBubble(text=text, is_user=is_user)
        self.chat_container.add_widget(bubble)
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)

    def start_listening(self) -> None:
        if not VOICE_SUPPORT:
            return
        try:
            stt.start()
            self.mic_btn.color = get_color_from_hex("#FF4A4A")
            Clock.schedule_interval(self.check_stt_results, 0.5)
        except Exception as e:
            self.add_message(f"[color=#FF4A4A]Microphone Error: {e}[/color]", is_user=False)

    def check_stt_results(self, dt):
        try:
            if hasattr(stt, 'listening') and not stt.listening:
                Clock.unschedule(self.check_stt_results)
                self.mic_btn.color = get_color_from_hex("#ECECEC")
                
                if hasattr(stt, 'results') and stt.results:
                    text = stt.results[0]
                    self.command.text = text
                    self.send_command()
        except Exception as e:
            Clock.unschedule(self.check_stt_results)
            self.mic_btn.color = get_color_from_hex("#ECECEC")

    def send_command(self) -> None:
        command = self.command.text.strip()
        api_key = self.settings.get("api_key", "").strip()
        
        if not command:
            return
        if not api_key:
            self.add_message("[color=#FF4A4A]Please enter your API Key in the settings (⚙) first.[/color]", is_user=False)
            self.toggle_settings(None)
            return
            
        self.add_message(command, is_user=True)
        self.send.disabled = True
        self.command.text = ""

        self.history.append({"role": "user", "content": command})

        def worker():
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://jarvis.mobile",
                    "X-Title": "JARVIS Mobile Standalone"
                }
                
                payload = {
                    "model": "google/gemini-2.5-flash",
                    "messages": self.history
                }
                
                body = json.dumps(payload).encode("utf-8")
                req = Request("https://openrouter.ai/api/v1/chat/completions", data=body, headers=headers, method="POST")
                
                with urlopen(req, timeout=90) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    reply = data["choices"][0]["message"]["content"]
                    self.history.append({"role": "assistant", "content": reply})
                    Clock.schedule_once(lambda _dt: self._finish_command(reply, None))
            except Exception as exc:
                self.history.pop()
                Clock.schedule_once(lambda _dt, e=exc: self._finish_command("", e))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_command(self, reply: str, error: Exception | None) -> None:
        self.send.disabled = False
        if error:
            self.add_message(f"[color=#FF4A4A]Connection Error: {error}[/color]", is_user=False)
        else:
            self.add_message(reply, is_user=False)
            if VOICE_SUPPORT:
                try:
                    tts.speak(reply)
                except Exception as e:
                    pass

class JarvisMobileApp(App):
    title = "J.A.R.V.I.S"
    def build(self):
        return JarvisClient()

if __name__ == "__main__":
    JarvisMobileApp().run()
