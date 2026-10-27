package android.view;
import android.content.Context;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
/** Small container model for host backends; no Android measure/layout engine. */
public class ViewGroup extends View {
    private final List<View> children = new ArrayList<>();
    public ViewGroup(Context context) { super(context); }
    public void addView(View child) {
        if (child == null) throw new NullPointerException("child");
        if (child.getContext() != getContext())
            throw new IllegalArgumentException("Views must share the same Context");
        children.add(child);
    }
    @Override public <T extends View> T findViewById(int targetId) {
        T self = super.findViewById(targetId);
        if (self != null) return self;
        for (View child : children) {
            T found = child.findViewById(targetId);
            if (found != null) return found;
        }
        return null;
    }
    public int getChildCount() { return children.size(); }
    public View getChildAt(int index) { return children.get(index); }
    public List<View> getChildrenForHost() { return Collections.unmodifiableList(children); }
}
