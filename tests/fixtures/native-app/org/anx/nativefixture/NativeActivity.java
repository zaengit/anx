package org.anx.nativefixture;
import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;
/** Compiled with the official Android SDK, not the ANX framework. */
public final class NativeActivity extends Activity {
    static {
        System.loadLibrary("anxfixture");
    }
    private native int nativeSum(int x, int y);
    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        int actual = nativeSum(7, 9);
        if (actual != 16) throw new AssertionError("JNI result: " + actual);
        System.out.println("[anx-jni] nativeSum(7,9)=" + actual);
        TextView label = new TextView(this);
        label.setText("Host JNI test: " + actual);
        setContentView(label);
    }
}
