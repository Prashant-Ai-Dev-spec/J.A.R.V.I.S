package com.prashant.jarvismobile;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.graphics.Path;
import android.os.Build;
import android.os.Bundle;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.List;
import java.util.Locale;

public class JarvisAccessibilityService extends AccessibilityService {
    private static JarvisAccessibilityService instance;

    public static boolean isActive() {
        return instance != null;
    }

    public static String runCommand(String command) {
        JarvisAccessibilityService service = instance;
        if (service == null) {
            return "Accessibility service disabled. Enable JARVIS Phone Control in Android Accessibility settings.";
        }
        return service.handleCommand(command);
    }

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
    }

    @Override
    public void onInterrupt() {
    }

    @Override
    public boolean onUnbind(android.content.Intent intent) {
        if (instance == this) {
            instance = null;
        }
        return super.onUnbind(intent);
    }

    private String handleCommand(String rawCommand) {
        String command = normalize(rawCommand);
        if (containsAny(command, "back", "peeche", "piche", "wapas")) {
            return performGlobalAction(GLOBAL_ACTION_BACK) ? "Back dabaya." : "Back action fail hua.";
        }
        if (containsAny(command, "home", "ghar")) {
            return performGlobalAction(GLOBAL_ACTION_HOME) ? "Home open kar diya." : "Home action fail hua.";
        }
        if (containsAny(command, "recent", "recents", "recent apps")) {
            return performGlobalAction(GLOBAL_ACTION_RECENTS) ? "Recent apps open kar diya." : "Recent apps action fail hua.";
        }
        if (containsAny(command, "notification", "notifications", "notification panel")) {
            return performGlobalAction(GLOBAL_ACTION_NOTIFICATIONS) ? "Notifications open kar diya." : "Notifications action fail hua.";
        }
        if (containsAny(command, "quick setting", "quick settings")) {
            return performGlobalAction(GLOBAL_ACTION_QUICK_SETTINGS) ? "Quick settings open kar diya." : "Quick settings action fail hua.";
        }
        if (command.startsWith("click ") || command.startsWith("tap ")) {
            String label = rawCommand.replaceFirst("(?i)^(click|tap)\\s+", "").trim();
            if (label.matches("\\d+\\s*,?\\s*\\d+")) {
                String[] parts = label.replace(",", " ").trim().split("\\s+");
                return tap(Integer.parseInt(parts[0]), Integer.parseInt(parts[1]))
                        ? "Screen par tap kar diya."
                        : "Tap fail hua.";
            }
            return clickText(label) ? label + " click kar diya." : label + " screen par nahi mila.";
        }
        if (command.startsWith("type ") || command.startsWith("write ") || command.startsWith("likho ")) {
            String text = rawCommand.replaceFirst("(?i)^(type|write|likho)\\s+", "").trim();
            return typeText(text) ? "Text type kar diya." : "Focused text field nahi mila.";
        }
        if (containsAny(command, "scroll down", "neeche", "niche")) {
            return scroll(true) ? "Scroll down kar diya." : "Scroll down fail hua.";
        }
        if (containsAny(command, "scroll up", "upar")) {
            return scroll(false) ? "Scroll up kar diya." : "Scroll up fail hua.";
        }
        return "Phone control command samajh nahi aaya.";
    }

    private boolean clickText(String label) {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null || label == null || label.trim().isEmpty()) {
            return false;
        }
        List<AccessibilityNodeInfo> matches = root.findAccessibilityNodeInfosByText(label.trim());
        for (AccessibilityNodeInfo node : matches) {
            AccessibilityNodeInfo target = clickableParent(node);
            if (target != null && target.performAction(AccessibilityNodeInfo.ACTION_CLICK)) {
                return true;
            }
        }
        return false;
    }

    private AccessibilityNodeInfo clickableParent(AccessibilityNodeInfo node) {
        AccessibilityNodeInfo current = node;
        while (current != null) {
            if (current.isClickable() && current.isEnabled()) {
                return current;
            }
            current = current.getParent();
        }
        return node;
    }

    private boolean typeText(String text) {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        AccessibilityNodeInfo target = findFocusedEditable(root);
        if (target == null) {
            target = findFirstEditable(root);
        }
        if (target == null) {
            return false;
        }
        Bundle args = new Bundle();
        args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text);
        return target.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args);
    }

    private AccessibilityNodeInfo findFocusedEditable(AccessibilityNodeInfo node) {
        if (node == null) return null;
        if (node.isFocused() && node.isEditable()) return node;
        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo found = findFocusedEditable(node.getChild(i));
            if (found != null) return found;
        }
        return null;
    }

    private AccessibilityNodeInfo findFirstEditable(AccessibilityNodeInfo node) {
        if (node == null) return null;
        if (node.isEditable()) return node;
        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo found = findFirstEditable(node.getChild(i));
            if (found != null) return found;
        }
        return null;
    }

    private boolean scroll(boolean forward) {
        AccessibilityNodeInfo scrollable = findScrollable(getRootInActiveWindow());
        if (scrollable != null) {
            int action = forward ? AccessibilityNodeInfo.ACTION_SCROLL_FORWARD : AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD;
            if (scrollable.performAction(action)) {
                return true;
            }
        }
        return swipe(forward);
    }

    private AccessibilityNodeInfo findScrollable(AccessibilityNodeInfo node) {
        if (node == null) return null;
        if (node.isScrollable()) return node;
        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo found = findScrollable(node.getChild(i));
            if (found != null) return found;
        }
        return null;
    }

    private boolean tap(int x, int y) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) return false;
        Path path = new Path();
        path.moveTo(x, y);
        GestureDescription gesture = new GestureDescription.Builder()
                .addStroke(new GestureDescription.StrokeDescription(path, 0, 80))
                .build();
        return dispatchGesture(gesture, null, null);
    }

    private boolean swipe(boolean forward) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) return false;
        int startY = forward ? 1450 : 650;
        int endY = forward ? 650 : 1450;
        Path path = new Path();
        path.moveTo(540, startY);
        path.lineTo(540, endY);
        GestureDescription gesture = new GestureDescription.Builder()
                .addStroke(new GestureDescription.StrokeDescription(path, 0, 360))
                .build();
        return dispatchGesture(gesture, null, null);
    }

    private String normalize(String value) {
        return String.valueOf(value == null ? "" : value).trim().toLowerCase(Locale.ROOT);
    }

    private boolean containsAny(String value, String... needles) {
        for (String needle : needles) {
            if (value.contains(needle)) return true;
        }
        return false;
    }
}
