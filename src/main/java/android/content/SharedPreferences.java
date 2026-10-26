package android.content;
import java.util.Map;
import java.util.Set;
/** Persistent, private subset; listeners and StringSet are not implemented. */
public interface SharedPreferences {
    Map<String, ?> getAll();
    String getString(String key, String fallback);
    int getInt(String key, int fallback);
    long getLong(String key, long fallback);
    float getFloat(String key, float fallback);
    boolean getBoolean(String key, boolean fallback);
    boolean contains(String key);
    Editor edit();
    interface Editor {
        Editor putString(String key, String value);
        Editor putInt(String key, int value);
        Editor putLong(String key, long value);
        Editor putFloat(String key, float value);
        Editor putBoolean(String key, boolean value);
        Editor remove(String key);
        Editor clear();
        boolean commit();
        void apply();
    }
}
