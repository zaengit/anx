package android.os;
import java.util.HashMap;
import java.util.Map;
/** Small, in-process Bundle subset. Parceling is not supported. */
public class Bundle {
    private final Map<String, Object> data = new HashMap<>();
    public Bundle() { }
    public Bundle(Bundle source) {
        if (source == null) throw new NullPointerException("source");
        data.putAll(source.data);
    }
    public void putAll(Bundle values) {
        if (values == null) throw new NullPointerException("values");
        data.putAll(values.data);
    }
    public void putString(String key, String value) { data.put(key, value); }
    public String getString(String key) { return (String) data.get(key); }
    public String getString(String key, String fallback) {
        String value = getString(key);
        return value == null ? fallback : value;
    }
    public void putInt(String key, int value) { data.put(key, Integer.valueOf(value)); }
    public int getInt(String key) { return getInt(key, 0); }
    public int getInt(String key, int fallback) {
        Object value = data.get(key);
        return value == null ? fallback : ((Integer) value).intValue();
    }
    public void putBoolean(String key, boolean value) { data.put(key, Boolean.valueOf(value)); }
    public boolean getBoolean(String key) { return getBoolean(key, false); }
    public boolean getBoolean(String key, boolean fallback) {
        Object value = data.get(key);
        return value == null ? fallback : ((Boolean) value).booleanValue();
    }
    public void putBundle(String key, Bundle value) { data.put(key, value); }
    public Bundle getBundle(String key) { return (Bundle) data.get(key); }
    public boolean containsKey(String key) { return data.containsKey(key); }
    public void remove(String key) { data.remove(key); }
    public int size() { return data.size(); }
    public void clear() { data.clear(); }
}
