package android.content.pm;
import android.content.Context;
import java.util.Collections;
import java.util.List;
/** Own-package query subset; does not enumerate host Android installations. */
public final class PackageManager {
    public static final int GET_ACTIVITIES = 1;
    public static final int GET_SERVICES = 4;
    public static final int GET_META_DATA = 128;
    private final Context context;
    public PackageManager(Context context) {
        if (context == null) throw new NullPointerException("context");
        this.context = context;
    }
    public static class NameNotFoundException extends Exception {
        public NameNotFoundException(String packageName) { super(packageName); }
    }
    private void checkOwn(String requested) throws NameNotFoundException {
        if (!context.getPackageName().equals(requested))
            throw new NameNotFoundException(requested);
    }
    public ApplicationInfo getApplicationInfo(String name, int flags)
            throws NameNotFoundException {
        checkOwn(name);
        ApplicationInfo result = new ApplicationInfo();
        result.packageName = name;
        return result;
    }
    public PackageInfo getPackageInfo(String name, int flags) throws NameNotFoundException {
        checkOwn(name);
        PackageInfo result = new PackageInfo();
        result.packageName = name;
        result.applicationInfo = getApplicationInfo(name, flags);
        // No stable package version or signing certificate is known.
        result.versionCode = 0;
        result.versionName = null;
        return result;
    }
    public List<PackageInfo> getInstalledPackages(int flags) {
        try { return Collections.singletonList(getPackageInfo(context.getPackageName(), flags)); }
        catch (NameNotFoundException impossible) { throw new IllegalStateException(impossible); }
    }
    public boolean hasSystemFeature(String name) { return false; }
}
