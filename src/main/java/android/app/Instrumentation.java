package android.app;
import android.content.Intent;
import android.os.Bundle;
/** In-process lifecycle dispatcher, without ActivityManager/Binder. */
public class Instrumentation {
    public Application newApplication(String className, String packageName) throws Exception {
        String name = className == null || "-".equals(className)
                ? Application.class.getName() : className;
        Class<?> type = Class.forName(name);
        if (!Application.class.isAssignableFrom(type))
            throw new IllegalArgumentException("Not an Application: " + name);
        Application app = (Application) type.getDeclaredConstructor().newInstance();
        app.attachHostPackage(packageName);
        app.attachHostApplication(app);
        return app;
    }
    public Activity newActivity(String className, Application app, Intent intent) throws Exception {
        Class<?> type = Class.forName(className);
        if (!Activity.class.isAssignableFrom(type))
            throw new IllegalArgumentException("Not an Activity: " + className);
        Activity activity = (Activity) type.getDeclaredConstructor().newInstance();
        activity.attachHostPackage(app.getPackageName());
        activity.attachHostApplication(app);
        activity.attachHostIntent(intent);
        return activity;
    }
    public void callApplicationOnCreate(Application app) { app.performCreateForHost(); }
    public void callActivityOnCreate(Activity activity, Bundle state) { activity.performCreate(state); }
    public void callActivityOnStart(Activity activity) { activity.performStart(); }
    public void callActivityOnResume(Activity activity) { activity.performResume(); }
    public void callActivityOnPause(Activity activity) { activity.performPause(); }
    public void callActivityOnStop(Activity activity) { activity.performStop(); }
    public void callActivityOnDestroy(Activity activity) { activity.performDestroy(); }
}
