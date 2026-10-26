package android.widget;
import android.content.Context;
import android.view.ViewGroup;
/** Vertical layout supported by experimental Wayland host backend. */
public class LinearLayout extends ViewGroup {
    public static final int HORIZONTAL = 0;
    public static final int VERTICAL = 1;
    private int orientation = VERTICAL;
    public LinearLayout(Context context) { super(context); }
    public void setOrientation(int orientation) {
        if (orientation != HORIZONTAL && orientation != VERTICAL)
            throw new IllegalArgumentException("invalid orientation");
        this.orientation = orientation;
    }
    public int getOrientation() { return orientation; }
}
