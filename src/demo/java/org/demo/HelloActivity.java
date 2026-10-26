package org.demo;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;

public final class HelloActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        TextView view = new TextView(this);
        view.setText("Halo dari API Android minimal!");
        setContentView(view);
    }
}
