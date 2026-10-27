package android.view;
import android.content.Context;
/** View API subset. No Android measure/layout/render pipeline yet. */
public class View {
    public interface OnClickListener { void onClick(View view); }
    public interface OnLongClickListener { boolean onLongClick(View view); }
    private final Context context;
    private OnClickListener clickListener;
    private OnLongClickListener longClickListener;
    private int id = NO_ID;
    public static final int NO_ID = -1;
    public View(Context context) {
        if (context == null) throw new NullPointerException("context");
        this.context = context;
    }
    public final Context getContext() { return context; }
    public void setId(int id) { this.id = id; }
    public int getId() { return id; }
    @SuppressWarnings("unchecked")
    public <T extends View> T findViewById(int targetId) {
        return targetId != NO_ID && id == targetId ? (T) this : null;
    }
    public void setOnClickListener(OnClickListener listener) { clickListener = listener; }
    public void setOnLongClickListener(OnLongClickListener listener) {
        longClickListener = listener;
    }
    public boolean performLongClick() {
        return longClickListener != null && longClickListener.onLongClick(this);
    }
    public boolean performClick() {
        if (clickListener == null) return false;
        clickListener.onClick(this);
        return true;
    }
    public String describeForHost() { return getClass().getName(); }
}
