package org.anx.tests;
import android.app.Application;
public final class ThrowingApplication extends Application {
    @Override public void onTerminate() { System.out.println("[test] app terminated despite pause failure"); }
}
