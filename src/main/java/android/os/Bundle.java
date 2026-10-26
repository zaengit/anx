package android.os;

import java.util.HashMap;
import java.util.Map;

/** Implementasi sangat minimal; bisa diperluas sesuai kebutuhan. */
public class Bundle {
    private final Map<String, Object> data = new HashMap<>();

    public void putString(String key, String value) { data.put(key, value); }
    public String getString(String key) { return (String) data.get(key); }
    public boolean containsKey(String key) { return data.containsKey(key); }
}
