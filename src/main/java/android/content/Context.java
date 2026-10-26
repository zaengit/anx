package android.content;
import android.app.Application;
import android.content.res.AssetManager;
import android.content.res.Resources;
/** Host-side Context subset; Android services/permissions are not emulated. */
public abstract class Context {
    private String packageName = "unknown";
    private Application application;
    private AssetManager assets = new AssetManager(null);
    public final String getPackageName() { return packageName; }
    public final Context getApplicationContext() { return application == null ? this : application; }
    public final AssetManager getAssets() { return assets; }
    public final Resources getResources() { return new Resources(assets); }
    /** Host-only configuration hook. */
    public final void attachHostPackage(String name) {
        if (name == null || name.isEmpty()) throw new IllegalArgumentException("Package name is required");
        packageName = name;
    }
    /** Host-only configuration hook. */
    public final void attachHostApplication(Application app) {
        if (app == null) throw new NullPointerException("application");
        application = app;
        assets = app == this ? assets : app.getAssets();
    }
    /** Host-only APK origin; does not confer a sandbox. */
    public final void attachHostApk(String path) { assets = new AssetManager(path); }
}
