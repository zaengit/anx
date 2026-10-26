package org.anx.host;
import android.os.SharedPreferences;
import java.io.File;
/** Host paths for ANX private-per-package files (not an OS sandbox). */
public final class AppStorage {
    private AppStorage() { }
    private static File root() {
        String path = System.getenv("ANX_APP_DATA_HOME");
        if (path == null || path.isEmpty()) {
            String home = System.getProperty("user.home");
            if (home == null || home.isEmpty()) throw new IllegalStateException("No user home");
            path = new File(new File(home, ".local/share/anx"), "apps").getPath();
        }
        return new File(path);
    }
    public static File directory(String packageName, String type) {
        if (packageName == null || !packageName.matches(
                "[A-Za-z_][A-Za-z0-9_]*(\\.[A-Za-z_][A-Za-z0-9_]*)+")) {
            throw new IllegalArgumentException("Invalid package name");
        }
        if (!"files".equals(type) && !"cache".equals(type) && !"prefs".equals(type))
            throw new IllegalArgumentException("Unknown app directory");
        File directory = new File(new File(root(), packageName), type);
        if (!directory.isDirectory() && !directory.mkdirs() && !directory.isDirectory())
            throw new IllegalStateException("Cannot create application directory: " + directory);
        return directory;
    }
    public static File namedFile(File directory, String name) {
        if (name == null || name.length() > 100 || name.isEmpty() || ".".equals(name)
                || "..".equals(name) || !name.matches("[A-Za-z0-9_.-]+")) {
            throw new IllegalArgumentException("Unsafe app-local filename");
        }
        return new File(directory, name);
    }
    public static SharedPreferences preferences(String packageName, String name) {
        return new FilePreferences(namedFile(directory(packageName, "prefs"), name + ".properties"));
    }
}
