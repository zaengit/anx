package org.anx.host;

import android.view.View;

/** Titik sambung untuk backend Wayland/GTK pada milestone berikutnya. */
public interface WindowBackend {
    void show(View view);
}
