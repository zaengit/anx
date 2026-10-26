package org.demo;
import android.app.Application;
public final class HelloApplication extends Application {
    @Override public void onCreate() {
        System.out.println("[demo] Application ready: " + getPackageName());
        android.util.Log.i("ANX", "Own package: " + getPackageManager()
                .getInstalledPackages(0).get(0).packageName);
        android.os.SharedPreferences preferences = getSharedPreferences("launches", MODE_PRIVATE);
        int count = preferences.getInt("count", 0) + 1;
        if (!preferences.edit().putInt("count", count).commit())
            throw new IllegalStateException("Preferences persist failed");
        System.out.println("[demo] Persistent launches: " + count);
    }
}
