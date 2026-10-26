package org.anx.external;
import android.app.Application;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.util.Log;
/** Compiled against Android SDK android.jar (never ANX's own stubs). */
public final class ExternalApplication extends Application {
    @Override public void onCreate() {
        super.onCreate();
        SharedPreferences preferences = getSharedPreferences("external", MODE_PRIVATE);
        int count = preferences.getInt("launches", 0) + 1;
        if (!preferences.edit().putInt("launches", count).commit())
            throw new IllegalStateException("SharedPreferences failed");
        try {
            if (!getPackageManager().getPackageInfo(getPackageName(), 0)
                    .packageName.equals(getPackageName()))
                throw new AssertionError("package identity");
        } catch (PackageManager.NameNotFoundException e) {
            throw new IllegalStateException(e);
        }
        Log.i("External", "SDK ABI matched: " + getPackageName());
    }
}
