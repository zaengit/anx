package android.view;
import android.content.Context;
/** View API subset. No Android measure/layout/render pipeline yet. */
public class View {
    public interface OnClickListener { void onClick(View view); }
    private final Context context;
    private OnClickListener clickListener;
    public View(Context context) {
        if (context == null) throw new NullPointerException("context");
        this.context = context;
    }
    public final Context getContext() { return context; }
    public void setOnClickListener(OnClickListener listener) { clickListener = listener; }
    public boolean performClick() {
        if (clickListener == null) return false;
        clickListener.onClick(this);
        return true;
    }
    public String describeForHost() { return getClass().getName(); }
}
