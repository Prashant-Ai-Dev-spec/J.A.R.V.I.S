package com.prashant.jarvismobile;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.telecom.Call;
import android.telecom.CallScreeningService;
import android.telephony.SmsManager;

import java.util.ArrayList;

public class NormalCallSecretaryService extends CallScreeningService {
    static final String PREFS = "jarvis_mobile";
    static final String KEY_ENABLED = "normal_call_secretary_enabled";
    static final String KEY_REPLY = "normal_call_secretary_reply";
    static final String KEY_LAST_NUMBER = "normal_call_last_number";
    static final String KEY_LAST_STATUS = "normal_call_last_status";
    static final String KEY_LAST_TIME = "normal_call_last_time";
    static final String DEFAULT_REPLY = BuildConfig.DEFAULT_CALL_REPLY;

    private static final String CHANNEL_ID = "jarvis_normal_call_secretary";

    @Override
    public void onScreenCall(Call.Details callDetails) {
        SharedPreferences prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        if (!prefs.getBoolean(KEY_ENABLED, false)) {
            return;
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q
                && callDetails.getCallDirection() != Call.Details.DIRECTION_INCOMING) {
            return;
        }

        String number = numberFromDetails(callDetails);
        String reply = prefs.getString(KEY_REPLY, DEFAULT_REPLY);
        if (reply == null || reply.trim().isEmpty()) {
            reply = DEFAULT_REPLY;
        }

        CallResponse response = new CallResponse.Builder()
                .setDisallowCall(true)
                .setRejectCall(true)
                .setSkipCallLog(false)
                .setSkipNotification(false)
                .build();
        respondToCall(callDetails, response);

        String status = "Call declined.";
        if (!number.isEmpty()) {
            status = sendSmsReply(number, reply);
        } else {
            status = "Call declined, but caller number was unavailable.";
        }

        prefs.edit()
                .putString(KEY_LAST_NUMBER, number)
                .putString(KEY_LAST_STATUS, status)
                .putLong(KEY_LAST_TIME, System.currentTimeMillis())
                .apply();
        showNotification(status);
    }

    private String numberFromDetails(Call.Details details) {
        Uri handle = details.getHandle();
        if (handle == null) return "";
        String number = handle.getSchemeSpecificPart();
        return number == null ? "" : number.trim();
    }

    private String sendSmsReply(String number, String message) {
        if (checkSelfPermission(Manifest.permission.SEND_SMS) != PackageManager.PERMISSION_GRANTED) {
            return "Call declined, but SMS permission is missing.";
        }
        try {
            SmsManager smsManager;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                smsManager = getSystemService(SmsManager.class);
            } else {
                smsManager = SmsManager.getDefault();
            }
            if (smsManager == null) {
                return "Call declined, but SMS service was unavailable.";
            }
            ArrayList<String> parts = smsManager.divideMessage(message);
            if (parts != null && parts.size() > 1) {
                smsManager.sendMultipartTextMessage(number, null, parts, null, null);
            } else {
                smsManager.sendTextMessage(number, null, message, null, null);
            }
            return "Call declined and SMS reply sent.";
        } catch (Exception exc) {
            return "Call declined, but SMS failed: " + exc.getMessage();
        }
    }

    private void showNotification(String text) {
        NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) return;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            return;
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    BuildConfig.ASSISTANT_DISPLAY_NAME + " Call Secretary",
                    NotificationManager.IMPORTANCE_DEFAULT
            );
            manager.createNotificationChannel(channel);
        }

        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);
        Notification notification = builder
                .setSmallIcon(android.R.drawable.sym_call_missed)
                .setContentTitle(BuildConfig.ASSISTANT_DISPLAY_NAME + " normal call secretary")
                .setContentText(text)
                .setAutoCancel(true)
                .build();
        manager.notify(9042, notification);
    }
}
