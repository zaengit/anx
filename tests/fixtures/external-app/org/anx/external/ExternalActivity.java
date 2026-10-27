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
        label.setText(R.string.screen_title);
        if (!"Selamat datang di ANX — ✓".equals(getString(R.string.utf8_probe)))
            throw new AssertionError("UTF-8 compiled string resource failed");
        System.out.println("[external] resources.arsc lookup ok");
        Button button = new Button(this);
        button.setText("Update");
        button.setOnClickListener(v -> {
            label.setText(getString(R.string.clicked_message));
            System.out.println("[external] click updated label");
        });
        content.addView(label);
        content.addView(button);
        setContentView(content);
    }
}
