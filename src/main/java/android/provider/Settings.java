package android.provider;
import android.content.ContentResolver;
/** Synthetic non-identifying Android ID for experimental ANX compatibility. */
public final class Settings {
    private Settings() { }
    public static final class Secure {
        public static final String ANDROID_ID = "android_id";
        private Secure() { }
        public static String getString(ContentResolver resolver, String name) {
            if (resolver == null) throw new NullPointerException("resolver");
            if (ANDROID_ID.equals(name)) return "anx-host-not-an-android-device";
            return null;
        }
    }
}
