package com.prashant.jarvismobile;

import android.Manifest;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.app.role.RoleManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.MediaStore;
import android.provider.Settings;
import android.speech.RecognizerIntent;
import android.speech.tts.TextToSpeech;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.core.content.FileProvider;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import org.json.JSONObject;

public class MainActivity extends Activity {
    private static final int REQUEST_SPEECH = 701;
    private static final int REQUEST_FILE_CHOOSER = 702;
    private static final int REQUEST_AUDIO_PERMISSION = 703;
    private static final int REQUEST_CALL_SECRETARY_PERMISSIONS = 704;
    private static final int REQUEST_CALL_SCREENING_ROLE = 705;

    private WebView webView;
    private SharedPreferences prefs;
    private TextToSpeech tts;
    private ValueCallback<Uri[]> fileCallback;
    private Uri pendingCameraUri;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences("jarvis_mobile", Context.MODE_PRIVATE);

        webView = new WebView(this);
        setContentView(webView);
        configureWebView();

        tts = new TextToSpeech(this, status -> {
            if (status == TextToSpeech.SUCCESS) {
                tts.setLanguage(new Locale("hi", "IN"));
                tts.setSpeechRate(1.02f);
            }
        });

        webView.loadUrl("file:///android_asset/mobile/index.html");
    }

    private void configureWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccessFromFileURLs(true);
        settings.setAllowUniversalAccessFromFileURLs(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        webView.addJavascriptInterface(new JarvisBridge(), "JarvisAndroid");
        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(PermissionRequest request) {
                runOnUiThread(() -> request.grant(request.getResources()));
            }

            @Override
            public boolean onShowFileChooser(
                    WebView view,
                    ValueCallback<Uri[]> filePathCallback,
                    FileChooserParams fileChooserParams
            ) {
                if (fileCallback != null) {
                    fileCallback.onReceiveValue(null);
                }
                fileCallback = filePathCallback;

                Intent contentIntent = new Intent(Intent.ACTION_GET_CONTENT);
                contentIntent.addCategory(Intent.CATEGORY_OPENABLE);
                contentIntent.setType("image/*");

                ArrayList<Intent> initialIntents = new ArrayList<>();
                Intent cameraIntent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
                if (cameraIntent.resolveActivity(getPackageManager()) != null) {
                    try {
                        File imageFile = File.createTempFile("jarvis_capture_", ".jpg", getExternalCacheDir());
                        pendingCameraUri = FileProvider.getUriForFile(
                                MainActivity.this,
                                getPackageName() + ".fileprovider",
                                imageFile
                        );
                        cameraIntent.putExtra(MediaStore.EXTRA_OUTPUT, pendingCameraUri);
                        cameraIntent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
                        initialIntents.add(cameraIntent);
                    } catch (IOException ignored) {
                        pendingCameraUri = null;
                    }
                }

                Intent chooser = Intent.createChooser(contentIntent, "Select image for JARVIS");
                chooser.putExtra(Intent.EXTRA_INITIAL_INTENTS, initialIntents.toArray(new Intent[0]));
                try {
                    startActivityForResult(chooser, REQUEST_FILE_CHOOSER);
                } catch (ActivityNotFoundException ex) {
                    fileCallback.onReceiveValue(null);
                    fileCallback = null;
                }
                return true;
            }
        });
    }

    private void startVoiceInput() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.RECORD_AUDIO}, REQUEST_AUDIO_PERMISSION);
            return;
        }

        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "hi-IN");
        intent.putExtra(RecognizerIntent.EXTRA_PROMPT, "Bolo bhai...");
        try {
            startActivityForResult(intent, REQUEST_SPEECH);
        } catch (ActivityNotFoundException ex) {
            postToJs("window.onNativeSpeechError && window.onNativeSpeechError('Speech recognition unavailable')");
        }
    }

    private void requestNormalCallSecretarySetup() {
        prefs.edit().putBoolean(NormalCallSecretaryService.KEY_ENABLED, true).apply();
        ArrayList<String> permissions = new ArrayList<>();
        addPermissionIfMissing(permissions, Manifest.permission.READ_PHONE_STATE);
        addPermissionIfMissing(permissions, Manifest.permission.READ_CALL_LOG);
        addPermissionIfMissing(permissions, Manifest.permission.SEND_SMS);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            addPermissionIfMissing(permissions, Manifest.permission.POST_NOTIFICATIONS);
        }
        if (!permissions.isEmpty()) {
            ActivityCompat.requestPermissions(
                    this,
                    permissions.toArray(new String[0]),
                    REQUEST_CALL_SECRETARY_PERMISSIONS
            );
            return;
        }
        requestCallScreeningRole();
    }

    private void addPermissionIfMissing(ArrayList<String> permissions, String permission) {
        if (ContextCompat.checkSelfPermission(this, permission) != PackageManager.PERMISSION_GRANTED) {
            permissions.add(permission);
        }
    }

    private void requestCallScreeningRole() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            return;
        }
        RoleManager roleManager = (RoleManager) getSystemService(Context.ROLE_SERVICE);
        if (roleManager == null || !roleManager.isRoleAvailable(RoleManager.ROLE_CALL_SCREENING)) {
            return;
        }
        if (!roleManager.isRoleHeld(RoleManager.ROLE_CALL_SCREENING)) {
            Intent intent = roleManager.createRequestRoleIntent(RoleManager.ROLE_CALL_SCREENING);
            startActivityForResult(intent, REQUEST_CALL_SCREENING_ROLE);
        }
    }

    private boolean hasCallScreeningRole() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            return false;
        }
        RoleManager roleManager = (RoleManager) getSystemService(Context.ROLE_SERVICE);
        return roleManager != null
                && roleManager.isRoleAvailable(RoleManager.ROLE_CALL_SCREENING)
                && roleManager.isRoleHeld(RoleManager.ROLE_CALL_SCREENING);
    }

    private String normalCallSecretaryStatus() {
        try {
            JSONObject json = new JSONObject();
            json.put("enabled", prefs.getBoolean(NormalCallSecretaryService.KEY_ENABLED, false));
            json.put("role_held", hasCallScreeningRole());
            json.put("read_phone_state", ContextCompat.checkSelfPermission(this, Manifest.permission.READ_PHONE_STATE) == PackageManager.PERMISSION_GRANTED);
            json.put("read_call_log", ContextCompat.checkSelfPermission(this, Manifest.permission.READ_CALL_LOG) == PackageManager.PERMISSION_GRANTED);
            json.put("send_sms", ContextCompat.checkSelfPermission(this, Manifest.permission.SEND_SMS) == PackageManager.PERMISSION_GRANTED);
            json.put("reply", prefs.getString(NormalCallSecretaryService.KEY_REPLY, NormalCallSecretaryService.DEFAULT_REPLY));
            json.put("last_number", prefs.getString(NormalCallSecretaryService.KEY_LAST_NUMBER, ""));
            json.put("last_status", prefs.getString(NormalCallSecretaryService.KEY_LAST_STATUS, ""));
            json.put("last_time", prefs.getLong(NormalCallSecretaryService.KEY_LAST_TIME, 0L));
            return json.toString();
        } catch (Exception exc) {
            return "{\"error\":\"" + exc.getMessage() + "\"}";
        }
    }

    private String mobileControlStatus() {
        try {
            JSONObject json = new JSONObject();
            json.put("accessibility_enabled", JarvisAccessibilityService.isActive());
            json.put("message", JarvisAccessibilityService.isActive()
                    ? "Phone control ready."
                    : "Enable JARVIS Phone Control in Android Accessibility settings.");
            return json.toString();
        } catch (Exception exc) {
            return "{\"error\":\"" + exc.getMessage() + "\"}";
        }
    }

    private void openAccessibilitySettings() {
        Intent intent = new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        startActivity(intent);
    }

    private String executeMobileCommand(String command) {
        String raw = command == null ? "" : command.trim();
        String lower = raw.toLowerCase(Locale.ROOT);
        if (raw.isEmpty()) {
            return jsonResult(false, false, "Phone command blank hai.");
        }

        String packageName = appPackageForCommand(lower);
        if (packageName != null) {
            boolean opened = openPackage(packageName);
            if (opened) {
                return jsonResult(true, true, appLabelForPackage(packageName) + " open kar diya.");
            }
            String fallbackUrl = webFallbackForPackage(packageName);
            if (fallbackUrl != null && openUrl(fallbackUrl)) {
                return jsonResult(true, true, "App installed nahi mila, website open kar di.");
            }
            return jsonResult(true, false, "Ye app phone me installed nahi mila.");
        }

        if (containsAny(lower, "settings", "setting kholo")) {
            startActivity(new Intent(Settings.ACTION_SETTINGS));
            return jsonResult(true, true, "Android settings open kar diya.");
        }
        if (containsAny(lower, "camera")) {
            Intent intent = new Intent(MediaStore.INTENT_ACTION_STILL_IMAGE_CAMERA);
            safeStart(intent);
            return jsonResult(true, true, "Camera open kar diya.");
        }
        if (containsAny(lower, "gallery", "photos", "photo")) {
            boolean ok = openPackage("com.google.android.apps.photos");
            if (!ok) {
                Intent intent = new Intent(Intent.ACTION_VIEW);
                intent.setType("image/*");
                safeStart(intent);
            }
            return jsonResult(true, true, "Photos/Gallery open kar diya.");
        }
        if (containsAny(lower, "accessibility", "phone control setup")) {
            openAccessibilitySettings();
            return jsonResult(true, true, "Accessibility settings open kar diya. JARVIS Phone Control enable karo.");
        }

        if (isAccessibilityCommand(lower)) {
            String message = JarvisAccessibilityService.runCommand(raw);
            boolean ready = JarvisAccessibilityService.isActive();
            return jsonResult(true, ready, message);
        }

        return jsonResult(false, false, "");
    }

    private boolean isAccessibilityCommand(String lower) {
        return containsAny(
                lower,
                "back", "peeche", "piche", "wapas", "home", "recent", "notification",
                "quick setting", "click ", "tap ", "type ", "write ", "likho ",
                "scroll", "neeche", "niche", "upar"
        );
    }

    private String appPackageForCommand(String lower) {
        Map<String, String> apps = new HashMap<>();
        apps.put("instagram", "com.instagram.android");
        apps.put("insta", "com.instagram.android");
        apps.put("whatsapp", "com.whatsapp");
        apps.put("youtube", "com.google.android.youtube");
        apps.put("you tube", "com.google.android.youtube");
        apps.put("chrome", "com.android.chrome");
        apps.put("browser", "com.android.chrome");
        apps.put("gmail", "com.google.android.gm");
        apps.put("mail", "com.google.android.gm");
        apps.put("facebook", "com.facebook.katana");
        apps.put("snapchat", "com.snapchat.android");
        apps.put("telegram", "org.telegram.messenger");
        for (Map.Entry<String, String> entry : apps.entrySet()) {
            if (lower.contains(entry.getKey()) && containsAny(lower, "open", "kholo", "khol", "chalao", "launch")) {
                return entry.getValue();
            }
        }
        return null;
    }

    private String appLabelForPackage(String packageName) {
        if ("com.instagram.android".equals(packageName)) return "Instagram";
        if ("com.whatsapp".equals(packageName)) return "WhatsApp";
        if ("com.google.android.youtube".equals(packageName)) return "YouTube";
        if ("com.android.chrome".equals(packageName)) return "Chrome";
        if ("com.google.android.gm".equals(packageName)) return "Gmail";
        if ("com.facebook.katana".equals(packageName)) return "Facebook";
        if ("com.snapchat.android".equals(packageName)) return "Snapchat";
        if ("org.telegram.messenger".equals(packageName)) return "Telegram";
        if ("com.google.android.apps.photos".equals(packageName)) return "Photos";
        return "App";
    }

    private String webFallbackForPackage(String packageName) {
        if ("com.instagram.android".equals(packageName)) return "https://www.instagram.com/";
        if ("com.google.android.youtube".equals(packageName)) return "https://www.youtube.com/";
        if ("com.facebook.katana".equals(packageName)) return "https://www.facebook.com/";
        if ("com.google.android.gm".equals(packageName)) return "https://mail.google.com/";
        if ("org.telegram.messenger".equals(packageName)) return "https://web.telegram.org/";
        return null;
    }

    private boolean openPackage(String packageName) {
        Intent launch = getPackageManager().getLaunchIntentForPackage(packageName);
        if (launch == null) return false;
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        return safeStart(launch);
    }

    private boolean openUrl(String url) {
        return safeStart(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
    }

    private boolean safeStart(Intent intent) {
        final boolean[] ok = {false};
        CountDownLatch latch = new CountDownLatch(1);
        runOnUiThread(() -> {
            try {
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(intent);
                ok[0] = true;
            } catch (Exception ignored) {
                ok[0] = false;
            } finally {
                latch.countDown();
            }
        });
        try {
            latch.await(2, TimeUnit.SECONDS);
        } catch (InterruptedException exc) {
            Thread.currentThread().interrupt();
        }
        return ok[0];
    }

    private String jsonResult(boolean handled, boolean ok, String message) {
        try {
            JSONObject json = new JSONObject();
            json.put("handled", handled);
            json.put("ok", ok);
            json.put("message", message);
            json.put("accessibility_enabled", JarvisAccessibilityService.isActive());
            return json.toString();
        } catch (Exception exc) {
            return "{\"handled\":true,\"ok\":false,\"message\":\"" + exc.getMessage() + "\"}";
        }
    }

    private boolean containsAny(String value, String... needles) {
        for (String needle : needles) {
            if (value.contains(needle)) return true;
        }
        return false;
    }

    private void postToJs(String script) {
        runOnUiThread(() -> webView.evaluateJavascript(script, null));
    }

    private String jsString(String value) {
        if (value == null) return "''";
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "") + "'";
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == REQUEST_SPEECH) {
            if (resultCode == RESULT_OK && data != null) {
                ArrayList<String> results = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);
                String text = results != null && !results.isEmpty() ? results.get(0) : "";
                postToJs("window.onNativeSpeechResult && window.onNativeSpeechResult(" + jsString(text) + ")");
            } else {
                postToJs("window.onNativeSpeechError && window.onNativeSpeechError('No speech captured')");
            }
            return;
        }

        if (requestCode == REQUEST_CALL_SCREENING_ROLE) {
            String message = hasCallScreeningRole()
                    ? "Normal call secretary enabled."
                    : "Call Screening role not granted.";
            postToJs("window.onNormalCallSecretaryUpdated && window.onNormalCallSecretaryUpdated(" + jsString(message) + ")");
            return;
        }

        if (requestCode == REQUEST_FILE_CHOOSER && fileCallback != null) {
            Uri[] results = null;
            if (resultCode == RESULT_OK) {
                if (data == null || data.getData() == null) {
                    if (pendingCameraUri != null) {
                        results = new Uri[]{pendingCameraUri};
                    }
                } else {
                    results = new Uri[]{data.getData()};
                }
            }
            fileCallback.onReceiveValue(results);
            fileCallback = null;
            pendingCameraUri = null;
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_AUDIO_PERMISSION) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                startVoiceInput();
            } else {
                postToJs("window.onNativeSpeechError && window.onNativeSpeechError('Microphone permission denied')");
            }
        } else if (requestCode == REQUEST_CALL_SECRETARY_PERMISSIONS) {
            requestCallScreeningRole();
            postToJs("window.onNormalCallSecretaryUpdated && window.onNormalCallSecretaryUpdated('Permissions updated')");
        }
    }

    @Override
    protected void onDestroy() {
        if (tts != null) {
            tts.stop();
            tts.shutdown();
        }
        super.onDestroy();
    }

    public class JarvisBridge {
        @JavascriptInterface
        public void startSpeech() {
            runOnUiThread(MainActivity.this::startVoiceInput);
        }

        @JavascriptInterface
        public void speak(String text) {
            if (tts != null && text != null && !text.trim().isEmpty()) {
                tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "jarvis-mobile-tts");
            }
        }

        @JavascriptInterface
        public String getSetting(String key) {
            return prefs.getString(key, "");
        }

        @JavascriptInterface
        public void setSetting(String key, String value) {
            prefs.edit().putString(key, value == null ? "" : value).apply();
        }

        @JavascriptInterface
        public void requestNormalCallSecretarySetup() {
            runOnUiThread(MainActivity.this::requestNormalCallSecretarySetup);
        }

        @JavascriptInterface
        public void setNormalCallSecretaryEnabled(boolean enabled) {
            prefs.edit().putBoolean(NormalCallSecretaryService.KEY_ENABLED, enabled).apply();
        }

        @JavascriptInterface
        public void setNormalCallSecretaryReply(String reply) {
            String clean = reply == null ? "" : reply.trim();
            if (clean.isEmpty()) {
                clean = NormalCallSecretaryService.DEFAULT_REPLY;
            }
            prefs.edit().putString(NormalCallSecretaryService.KEY_REPLY, clean).apply();
        }

        @JavascriptInterface
        public String normalCallSecretaryStatus() {
            return MainActivity.this.normalCallSecretaryStatus();
        }

        @JavascriptInterface
        public String mobileControlStatus() {
            return MainActivity.this.mobileControlStatus();
        }

        @JavascriptInterface
        public void openAccessibilitySettings() {
            runOnUiThread(MainActivity.this::openAccessibilitySettings);
        }

        @JavascriptInterface
        public String executeMobileCommand(String command) {
            return MainActivity.this.executeMobileCommand(command);
        }
    }
}
