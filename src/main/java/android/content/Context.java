package android.content;
import android.app.Application;
import android.content.res.AssetManager;
import android.content.res.Resources;
import android.content.pm.PackageManager;
import android.content.SharedPreferences;
import org.anx.host.AppStorage;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.FileNotFoundException;
/** Host-side Context subset; Android services/permissions are not emulated. */
public abstract class Context {
    public static final int MODE_PRIVATE = 0;
    public static final int MODE_APPEND = 0x8000;
    private String packageName = "unknown";
    private Application application;
    private AssetManager assets = new AssetManager(null);
    public final String getPackageName() { return packageName; }
    public final Context getApplicationContext() { return application == null ? this : application; }
    public final AssetManager getAssets() { return assets; }
    public final Resources getResources() { return new Resources(assets); }
    public final String getString(int id) { return getResources().getString(id); }
    public final CharSequence getText(int id) { return getResources().getText(id); }
    public final PackageManager getPackageManager() { return new PackageManager(this); }
    public final File getFilesDir() { return AppStorage.directory(packageName, "files"); }
    public final File getCacheDir() { return AppStorage.directory(packageName, "cache"); }
    public final SharedPreferences getSharedPreferences(String name, int mode) {
        if (mode != MODE_PRIVATE) throw new IllegalArgumentException("Only MODE_PRIVATE is supported");
        return AppStorage.preferences(packageName, name);
    }
    public final FileInputStream openFileInput(String name) throws FileNotFoundException {
        return new FileInputStream(AppStorage.namedFile(getFilesDir(), name));
    }
    public final FileOutputStream openFileOutput(String name, int mode) throws FileNotFoundException {
        if (mode != MODE_PRIVATE && mode != MODE_APPEND)
            throw new IllegalArgumentException("Unsupported file mode");
        return new FileOutputStream(AppStorage.namedFile(getFilesDir(), name), mode == MODE_APPEND);
    }
    public final boolean deleteFile(String name) {
        return AppStorage.namedFile(getFilesDir(), name).delete();
    }
    /** Host-only configuration hook. */
    public final void attachHostPackage(String name) {
        if (name == null || !name.matches("[A-Za-z_][A-Za-z0-9_]*(\\.[A-Za-z_][A-Za-z0-9_]*)+"))
            throw new IllegalArgumentException("Invalid Android package name");
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
