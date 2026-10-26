package android.content;

/** Subset API untuk pembuktian konsep; bukan Android Framework lengkap. */
public abstract class Context {
    private String packageName = "unknown";

    public final String getPackageName() {
        return packageName;
    }

    /** Internal compatibility-layer hook, bukan Android public API. */
    public final void attachHostPackage(String name) {
        if (name == null || name.isEmpty()) {
            throw new IllegalArgumentException("Package name is required");
        }
        packageName = name;
    }
}
