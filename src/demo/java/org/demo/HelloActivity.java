package org.demo;
import android.app.Activity;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
public final class HelloActivity extends Activity {
    @Override protected void onCreate(Bundle savedInstanceState) {
        LinearLayout layout = new LinearLayout(this);
        final TextView label = new TextView(this);
        label.setText("Halo dari API Android minimal!");
        Button button = new Button(this);
        button.setText("Klik saya");
        button.setOnClickListener(v -> label.setText("Tombol berhasil diklik!"));
        layout.addView(label);
        layout.addView(button);
        setContentView(layout);
    }
}
