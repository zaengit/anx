package android.widget;
import android.content.Context;
/** Click-capable API subset; desktop input requires a GUI backend. */
public class Button extends TextView {
    public Button(Context context) { super(context); }
    @Override public String describeForHost() { return "Button: " + getText(); }
}
