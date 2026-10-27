package org.anx.nested;
import android.app.Activity;
import android.os.Bundle;
import android.widget.Button;
import android.widget.TextView;

/** Compiled solely against official Android SDK android.jar, not ANX classes. */
public final class NestedActivity extends Activity {
    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(R.layout.activity_main);
        final TextView label = findViewById(R.id.status);
        Button button = findViewById(R.id.update_button);
        if (label == null || button == null ||
                findViewById(0x7f7fffff) != null ||
                !getString(R.string.nested_ready).contentEquals(label.getText()))
            throw new AssertionError("Nested XML view ID lookup failed");
        System.out.println("[nested] XML hierarchy and IDs resolved");
        button.setOnClickListener(v -> {
            label.setText(R.string.nested_clicked);
            if (!getString(R.string.nested_clicked).contentEquals(label.getText()))
                throw new AssertionError("Nested XML label did not update");
            System.out.println("[nested] click updated label");
        });
    }
}
