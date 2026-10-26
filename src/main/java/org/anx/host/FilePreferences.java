package org.anx.host;
import android.content.SharedPreferences;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
/** Typed properties persisted by atomic rename on Linux. Intra-process serialized writes. */
final class FilePreferences implements SharedPreferences {
    private static final int MAX_FILE_BYTES = 1024 * 1024;
    private final File file;
    FilePreferences(File file) { this.file = file; }
    private static void key(String name) {
        if (name == null || name.length() > 256) throw new IllegalArgumentException("Invalid preferences key");
    }
    private Map<String, Object> load() {
        Map<String, Object> values = new HashMap<>();
        if (!file.exists()) return values;
        if (file.length() > MAX_FILE_BYTES) throw new IllegalStateException("Preferences file too large");
        Properties props = new Properties();
        try (FileInputStream input = new FileInputStream(file)) { props.load(input); }
        catch (IOException e) { throw new IllegalStateException("Preferences read failed", e); }
        for (String k : props.stringPropertyNames()) {
            String v = props.getProperty(k);
            if (v.length() < 2 || v.charAt(1) != ':') continue;
            try {
                switch (v.charAt(0)) {
                    case 'S': values.put(k, v.substring(2)); break;
                    case 'I': values.put(k, Integer.valueOf(v.substring(2))); break;
                    case 'L': values.put(k, Long.valueOf(v.substring(2))); break;
                    case 'F': values.put(k, Float.valueOf(v.substring(2))); break;
                    case 'B': values.put(k, Boolean.valueOf(v.substring(2))); break;
                    default: break;
                }
            } catch (NumberFormatException ignored) { /* Ignore corrupted keys. */ }
        }
        return values;
    }
    private static String typed(Object value) {
        if (value instanceof String) return "S:" + value;
        if (value instanceof Integer) return "I:" + value;
        if (value instanceof Long) return "L:" + value;
        if (value instanceof Float) return "F:" + value;
        if (value instanceof Boolean) return "B:" + value;
        throw new IllegalArgumentException("Unsupported preferences type");
    }
    private void save(Map<String, Object> data) throws IOException {
        Properties props = new Properties();
        for (Map.Entry<String, Object> entry : data.entrySet()) {
            key(entry.getKey());
            String serial = typed(entry.getValue());
            if (serial.length() > 4096) throw new IOException("Preference value too large");
            props.setProperty(entry.getKey(), serial);
        }
        File temporary = File.createTempFile(".anx-", ".tmp", file.getParentFile());
        try {
            try (FileOutputStream output = new FileOutputStream(temporary)) {
                props.store(output, "ANX preferences");
                output.getFD().sync();
            }
            if (temporary.length() > MAX_FILE_BYTES) throw new IOException("Preferences size limit");
            if (!temporary.renameTo(file)) throw new IOException("Atomic rename failed");
        } finally {
            if (temporary.exists()) temporary.delete();
        }
    }
    @Override public Map<String, ?> getAll() {
        synchronized (FilePreferences.class) { return Collections.unmodifiableMap(load()); }
    }
    private Object get(String k) { key(k); synchronized (FilePreferences.class) { return load().get(k); } }
    @Override public boolean contains(String k) { key(k); synchronized (FilePreferences.class) { return load().containsKey(k); } }
    @Override public String getString(String k, String d) { Object v = get(k); return v == null ? d : (String)v; }
    @Override public int getInt(String k, int d) { Object v = get(k); return v == null ? d : (Integer)v; }
    @Override public long getLong(String k, long d) { Object v = get(k); return v == null ? d : (Long)v; }
    @Override public float getFloat(String k, float d) { Object v = get(k); return v == null ? d : (Float)v; }
    @Override public boolean getBoolean(String k, boolean d) { Object v = get(k); return v == null ? d : (Boolean)v; }
    @Override public Editor edit() { return new Changes(); }
    private final class Changes implements Editor {
        private final Map<String, Object> values = new HashMap<>();
        private final Set<String> removals = new HashSet<>();
        private boolean clear;
        private Editor put(String k, Object value) {
            key(k);
            values.put(k, value);
            removals.remove(k);
            return this;
        }
        @Override public Editor putString(String k, String v) {
            if (v == null) return remove(k);
            return put(k, v);
        }
        @Override public Editor putInt(String k, int v) { return put(k, Integer.valueOf(v)); }
        @Override public Editor putLong(String k, long v) { return put(k, Long.valueOf(v)); }
        @Override public Editor putFloat(String k, float v) { return put(k, Float.valueOf(v)); }
        @Override public Editor putBoolean(String k, boolean v) { return put(k, Boolean.valueOf(v)); }
        @Override public Editor remove(String k) {
            key(k);
            values.remove(k);
            removals.add(k);
            return this;
        }
        @Override public Editor clear() { clear = true; return this; }
        @Override public boolean commit() {
            synchronized (FilePreferences.class) {
                try {
                    Map<String, Object> result = clear ? new HashMap<String, Object>() : load();
                    for (String name : removals) result.remove(name);
                    result.putAll(values);
                    save(result);
                    return true;
                } catch (IOException | IllegalStateException ex) {
                    System.err.println("[anx] preferences commit failed: " + ex);
                    return false;
                }
            }
        }
        @Override public void apply() {
            if (!commit()) throw new IllegalStateException("Preferences apply failed");
        }
    }
}
