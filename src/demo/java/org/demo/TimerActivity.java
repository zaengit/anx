package org.demo;
import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.widget.TextView;
/** Regression fixture: scheduled callbacks require a running GUI event loop. */
public final class TimerActivity extends Activity {
    private TextView label;
    @Override protected void onCreate(Bundle state) {
        label = new TextView(this);
        label.setText("Waiting for Handler");
        setContentView(label);
    }
    @Override protected void onResume() {
        new Handler().postDelayed(() -> {
            label.setText("Delayed callback fired");
            System.out.println("[demo] Delayed Handler fired");
        }, 200);
    }
}
