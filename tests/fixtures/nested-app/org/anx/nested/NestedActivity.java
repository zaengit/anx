package org.anx.nested;
import android.app.Activity;
import android.os.Bundle;
import android.widget.Button;
import android.view.View;
import android.content.res.Resources;
import android.widget.TextView;

/** Compiled solely against official Android SDK android.jar, not ANX classes. */
public final class NestedActivity extends Activity {
    private TextView label;
    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(R.layout.activity_main);
        label = findViewById(R.id.status);
        Button button = findViewById(R.id.update_button);
        if (label == null || button == null ||
                findViewById(0x7f7fffff) != null ||
                !getString(R.string.nested_ready).contentEquals(label.getText()))
            throw new AssertionError("Nested XML view ID lookup failed");
        System.out.println("[nested] XML hierarchy and IDs resolved");
        try {
            setContentView(R.layout.bad_onclick);
            throw new AssertionError("Unsupported XML onClick was accepted");
        } catch (Resources.NotFoundException expected) {
            if (!expected.getMessage().contains("Missing public Activity method"))
                throw expected;
        }
        if (findViewById(R.id.status) != label)
            throw new AssertionError("A rejected layout replaced the existing view tree");
        System.out.println("[nested] invalid XML callback rejected");
    }
    /** Public method bound from android:onClick in XML, no Java listener setup. */
    public void updateViaXml(View clicked) {
        if (clicked.getId() != R.id.update_button)
            throw new AssertionError("XML callback received incorrect view");
        label.setText(R.string.nested_clicked);
        if (!getString(R.string.nested_clicked).contentEquals(label.getText()))
            throw new AssertionError("Nested XML label did not update");
        System.out.println("[nested] XML android:onClick updated label");
    }
}
