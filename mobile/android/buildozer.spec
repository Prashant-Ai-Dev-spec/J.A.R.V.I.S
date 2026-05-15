[app]
title = J.A.R.V.I.S
package.name = jarvis
package.domain = in.prashantbhagat
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0.0
requirements = python3,kivy,plyer,requests
orientation = portrait
fullscreen = 0
android.permissions = INTERNET, RECORD_AUDIO
android.api = 35
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
