package org.anx.external;
import android.app.Activity;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
/** Independent Android-SDK-compiled UI test, not compiled against ANX classes. */
public final class ExternalActivity extends Activity {
    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        final TextView label = new TextView(this);
        label.setText("External APK from Android SDK");
        Button button = new Button(this);
        button.setText("Update");
        button.setOnClickListener(v -> {
            label.setText("External button clicked");
            System.out.println("[external] click updated label");
        });
        content.addView(label);
        content.addView(button);
        setContentView(content);
    }
}
