package org.anx.host;
import android.view.View;
import android.view.ViewGroup;
public final class ConsoleBackend implements WindowBackend {
    @Override public void show(View view) {
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (View child : group.getChildrenForHost()) show(child);
        } else {
            System.out.println("[linux-console-backend] "
                    + (view == null ? "(no view)" : view.describeForHost()));
        }
    }
}
