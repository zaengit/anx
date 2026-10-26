package android.content;
import android.os.Bundle;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;
/** In-process explicit intents only; no Binder or Android intent resolution. */
public class Intent {
    public static final String ACTION_MAIN = "android.intent.action.MAIN";
    public static final String CATEGORY_LAUNCHER = "android.intent.category.LAUNCHER";
    private String action;
    private String component;
    private final Set<String> categories = new HashSet<>();
    private Bundle extras;
    public Intent() { }
    public Intent(String action) { this.action = action; }
    public Intent(Context context, Class<?> cls) {
        if (context == null || cls == null) throw new NullPointerException("context/class");
        component = cls.getName();
    }
    public Intent setAction(String value) { action = value; return this; }
    public String getAction() { return action; }
    public Intent setClassName(String packageName, String className) {
        if (packageName == null || packageName.isEmpty() || className == null || className.isEmpty()) {
            throw new IllegalArgumentException("package and class are required");
        }
        component = className.startsWith(".") ? packageName + className
                : className.indexOf('.') < 0 ? packageName + "." + className : className;
        return this;
    }
    public String getComponentClassNameForHost() { return component; }
    public Intent addCategory(String category) {
        if (category == null) throw new NullPointerException("category");
        categories.add(category);
        return this;
    }
    public boolean hasCategory(String category) { return categories.contains(category); }
    public Set<String> getCategories() { return Collections.unmodifiableSet(categories); }
    public Intent putExtra(String key, String value) { extras().putString(key, value); return this; }
    public Intent putExtra(String key, int value) { extras().putInt(key, value); return this; }
    public Intent putExtra(String key, boolean value) { extras().putBoolean(key, value); return this; }
    public String getStringExtra(String key) { return extras == null ? null : extras.getString(key); }
    public int getIntExtra(String key, int fallback) {
        return extras == null ? fallback : extras.getInt(key, fallback);
    }
    public boolean getBooleanExtra(String key, boolean fallback) {
        return extras == null ? fallback : extras.getBoolean(key, fallback);
    }
    public Bundle getExtras() { return extras == null ? null : new Bundle(extras); }
    public Intent putExtras(Bundle values) {
        extras().putAll(values);
        return this;
    }
    private Bundle extras() { if (extras == null) extras = new Bundle(); return extras; }
}
