# J.A.R.V.I.S Mobile

The mobile app is a companion controller. Run `jarvis_web.py` on the computer that owns the real JARVIS brain, then point the Android/iOS app at that computer's LAN address.

## Android APK

Buildozer builds APKs from Linux or WSL:

```bash
cd mobile/android
buildozer -v android debug
```

The APK will be created under `mobile/android/bin/`.
The repo script `scripts/build_android_apk.sh` creates a local virtual environment first, then runs Buildozer.

## iOS

The same API/client structure can be ported with Kivy iOS or replaced by the PWA in `web/`. Apple requires macOS and Xcode for signing and device builds.
