package android.view;

import android.content.Context;

/** Representasi widget minimum. Belum ada renderer Wayland. */
public class View {
    private final Context context;

    public View(Context context) {
        if (context == null) throw new NullPointerException("context");
        this.context = context;
    }

    public final Context getContext() { return context; }

    public String describeForHost() { return getClass().getName(); }
}
