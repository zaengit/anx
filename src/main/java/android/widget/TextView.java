package android.widget;

import android.content.Context;
import android.view.View;

/** Hanya API TextView yang dibutuhkan oleh demo. */
public class TextView extends View {
    private CharSequence text = "";

    public TextView(Context context) { super(context); }
    public void setText(CharSequence text) { this.text = text == null ? "" : text; }
    public void setText(int resourceId) { setText(getContext().getText(resourceId)); }
    public CharSequence getText() { return text; }

    @Override
    public String describeForHost() { return "TextView: " + text; }
}
