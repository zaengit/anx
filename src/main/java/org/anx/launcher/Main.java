package org.anx.launcher;

import android.app.Activity;
import android.os.Bundle;
import org.anx.host.ConsoleBackend;
import org.anx.host.WindowBackend;

/** Dapat dijalankan oleh Java VM untuk smoke test atau ART (dalvikvm64). */
public final class Main {
    private Main() { }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("Usage: org.anx.launcher.Main <activity-class>");
            System.exit(2);
        }
        Class<?> loaded = Class.forName(args[0]);
        if (!Activity.class.isAssignableFrom(loaded)) {
            throw new IllegalArgumentException("Not an Activity: " + loaded.getName());
        }

        Activity activity = (Activity) loaded.getDeclaredConstructor().newInstance();
        int dot = loaded.getName().lastIndexOf('.');
        activity.attachHostPackage(dot > 0 ? loaded.getName().substring(0, dot) : "demo");

        WindowBackend backend = new ConsoleBackend();
        boolean created = false;
        boolean started = false;
        boolean resumed = false;
        try {
            System.out.println("[anx] onCreate");
            activity.performCreate(new Bundle());
            created = true;
            System.out.println("[anx] onStart");
            activity.performStart();
            started = true;
            System.out.println("[anx] onResume");
            activity.performResume();
            resumed = true;
            backend.show(activity.getContentViewForHost());
        } finally {
            if (resumed) {
                System.out.println("[anx] onPause");
                activity.performPause();
            }
            if (started) {
                System.out.println("[anx] onStop");
                activity.performStop();
            }
            if (created) {
                System.out.println("[anx] onDestroy");
                activity.performDestroy();
            }
        }
    }
}
