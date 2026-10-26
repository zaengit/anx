package org.anx.tests;
import android.app.Application;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.util.Log;
public final class LoggingPackageTest {
    private static void check(boolean okay, String reason) {
        if (!okay) throw new AssertionError(reason);
    }
    public static void main(String[] args) throws Exception {
        Application app = new Application();
        app.attachHostPackage("org.anx.fixture");
        PackageManager manager = app.getPackageManager();
        PackageInfo own = manager.getPackageInfo(app.getPackageName(), 0);
        check("org.anx.fixture".equals(own.packageName), "own package identity");
        check("org.anx.fixture".equals(own.applicationInfo.packageName), "application info");
        check(own.versionCode == 0 && own.versionName == null, "unknown metadata is not invented");
        check(manager.getInstalledPackages(0).size() == 1, "only own package visible");
        check(!manager.hasSystemFeature("android.hardware.camera"), "unsupported feature");
        try {
            manager.getPackageInfo("com.someone.else", 0);
            throw new AssertionError("unknown package accepted");
        } catch (PackageManager.NameNotFoundException expected) { }
        check(Log.i("Test", "info") == 4, "log return");
        check(Log.e("Test", "failure") == 7, "error log");
        check(Log.isLoggable("Test", Log.DEBUG), "log level");
        check(Log.getStackTraceString(new RuntimeException("marker")).contains("marker"),
                "stack trace reporting");
        System.out.println("[PASS] Android logging and own-package query subset");
    }
}
