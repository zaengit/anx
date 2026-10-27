package android.widget;
import android.content.Context;
/** Console-only compatibility: does NOT show an Android popup or native toast. */
public final class Toast {
    public static final int LENGTH_SHORT = 0;
    public static final int LENGTH_LONG = 1;
    private final CharSequence text;
    private Toast(CharSequence text) { this.text = text; }
    public static Toast makeText(Context context, CharSequence text, int duration) {
        if (context == null) throw new NullPointerException("context");
        if (duration != LENGTH_SHORT && duration != LENGTH_LONG)
            throw new IllegalArgumentException("Unknown toast length");
        return new Toast(text);
    }
    public static Toast makeText(Context context, int resourceId, int duration) {
        if (context == null) throw new NullPointerException("context");
        return makeText(context, context.getText(resourceId), duration);
    }
    public void show() { System.out.println("[anx-toast/console] " + text); }
}
