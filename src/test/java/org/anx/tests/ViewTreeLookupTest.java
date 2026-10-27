package org.anx.tests;
import android.app.Activity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
public final class ViewTreeLookupTest {
    public static void main(String[] args) {
        Activity activity = new Activity();
        if (activity.findViewById(42) != null)
            throw new AssertionError("Missing content must return null");
        LinearLayout outer = new LinearLayout(activity);
        LinearLayout inner = new LinearLayout(activity);
        TextView label = new TextView(activity);
        label.setId(42);
        Button button = new Button(activity);
        button.setId(43);
        inner.addView(label);
        inner.addView(button);
        outer.addView(inner);
        activity.setContentView(outer);
        if (activity.findViewById(42) != label || activity.findViewById(43) != button ||
                outer.findViewById(43) != button || outer.findViewById(44) != null ||
                outer.findViewById(View.NO_ID) != null)
            throw new AssertionError("Recursive Android view ID lookup failed");
        button.setOnClickListener(v -> label.setText("updated"));
        if (!button.performClick() || !"updated".contentEquals(label.getText()))
            throw new AssertionError("View ID/click listener integration failed");
        System.out.println("[PASS] Nested view IDs and button callbacks");
    }
}
