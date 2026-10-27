package org.anx.tests;
import android.app.Application;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.os.Build;
import android.provider.Settings;
import android.view.View;
import android.widget.TextView;
import android.widget.Toast;
public final class SyntheticDeviceCompatTest {
    public static void main(String[] args) {
        Application app = new Application();
        app.attachHostPackage("org.anx.synthetic");
        String id = Settings.Secure.getString(app.getContentResolver(), Settings.Secure.ANDROID_ID);
        if (!"anx-host-not-an-android-device".equals(id) || Build.VERSION.SDK_INT != 26
                || !Build.VERSION.RELEASE.startsWith("ANX-"))
            throw new AssertionError("Host identity may not claim real Android hardware");
        ClipboardManager clip = (ClipboardManager) app.getSystemService(Context.CLIPBOARD_SERVICE);
        clip.setPrimaryClip(ClipData.newPlainText("test", "in-memory"));
        if (!"in-memory".contentEquals(clip.getPrimaryClip().getItemAt(0).getText()))
            throw new AssertionError("Isolated clipboard failed");
        TextView label = new TextView(app);
        label.setOnLongClickListener(v -> {
            clip.setPrimaryClip(ClipData.newPlainText("label", label.getText()));
            return true;
        });
        label.setText("hello");
        if (!label.performLongClick() ||
                !"hello".contentEquals(clip.getPrimaryClip().getItemAt(0).getText()))
            throw new AssertionError("Long click listener failed");
        Toast.makeText(app, "headless toast", Toast.LENGTH_LONG).show();
        System.out.println("[PASS] Synthetic Android metadata, in-process clipboard and long-click");
    }
}
