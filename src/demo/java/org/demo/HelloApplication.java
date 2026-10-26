package org.demo;
import android.app.Application;
public final class HelloApplication extends Application {
    @Override public void onCreate() {
        System.out.println("[demo] Application ready: " + getPackageName());
    }
}
