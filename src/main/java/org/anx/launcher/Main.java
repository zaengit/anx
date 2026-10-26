package org.anx.launcher;
import android.app.Activity;
import android.app.Application;
import android.app.Instrumentation;
import android.content.Intent;
import android.os.Bundle;
import android.os.Looper;
import org.anx.host.ConsoleBackend;
import org.anx.host.WindowBackend;
/** ANX host ART/JVM entry: APK metadata is validated by the Python loader. */
public final class Main {
    private Main() { }
    public static void main(String[] args) throws Exception {
        if (args.length < 1 || args.length > 4) {
            System.err.println("Usage: org.anx.launcher.Main <activity> [package] [application|-] [apk-path]");
            System.exit(2);
        }
        String activityClass = args[0];
        int dot = activityClass.lastIndexOf('.');
        String packageName = args.length >= 2 ? args[1]
                : dot > 0 ? activityClass.substring(0, dot) : "demo";
        String applicationClass = args.length >= 3 ? args[2] : "-";
        String apkPath = args.length >= 4 ? args[3] : null;
        Looper.prepareMainLooper();
        Looper main = Looper.myLooper();
        Instrumentation instrumentation = new Instrumentation();
        Application app = instrumentation.newApplication(applicationClass, packageName);
        if (apkPath != null) app.attachHostApk(apkPath);
        Intent launch = new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
                .setClassName(packageName, activityClass);
        Activity activity = null;
        boolean appCreated = false;
        boolean created = false;
        boolean started = false;
        boolean resumed = false;
        Throwable failure = null;
        try {
            System.out.println("[anx] Application.onCreate");
            instrumentation.callApplicationOnCreate(app);
            appCreated = true;
            activity = instrumentation.newActivity(activityClass, app, launch);
            System.out.println("[anx] onCreate");
            instrumentation.callActivityOnCreate(activity, new Bundle());
            created = true;
            System.out.println("[anx] onStart");
            instrumentation.callActivityOnStart(activity);
            started = true;
            System.out.println("[anx] onResume");
            instrumentation.callActivityOnResume(activity);
            resumed = true;
            main.drainForHost();
            WindowBackend backend = new ConsoleBackend();
            backend.show(activity.getContentViewForHost());
        } catch (Throwable error) {
            failure = error;
        } finally {
            // Run all cleanup transitions, even if an earlier callback fails.
            try {
                if (resumed) {
                    System.out.println("[anx] onPause");
                    instrumentation.callActivityOnPause(activity);
                }
            } catch (Throwable error) { failure = addFailure(failure, error); }
            try {
                if (started) {
                    System.out.println("[anx] onStop");
                    instrumentation.callActivityOnStop(activity);
                }
            } catch (Throwable error) { failure = addFailure(failure, error); }
            try {
                if (created) {
                    System.out.println("[anx] onDestroy");
                    instrumentation.callActivityOnDestroy(activity);
                }
            } catch (Throwable error) { failure = addFailure(failure, error); }
            try {
                if (appCreated) {
                    System.out.println("[anx] Application.onTerminate");
                    app.performTerminateForHost();
                }
            } catch (Throwable error) { failure = addFailure(failure, error); }
            main.quit();
        }
        if (failure != null) {
            if (failure instanceof Exception) throw (Exception) failure;
            if (failure instanceof Error) throw (Error) failure;
            throw new RuntimeException(failure);
        }
    }
    private static Throwable addFailure(Throwable first, Throwable next) {
        if (first == null) return next;
        if (first != next) first.addSuppressed(next);
        return first;
    }
}
