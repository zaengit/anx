package org.anx.host;

import android.view.View;

public final class ConsoleBackend implements WindowBackend {
    @Override
    public void show(View view) {
        System.out.println("[linux-console-backend] "
                + (view == null ? "(no view)" : view.describeForHost()));
    }
}
