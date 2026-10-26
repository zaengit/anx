package org.anx.tests;
import android.app.Activity;
import android.os.Bundle;
public final class ThrowingActivity extends Activity {
    @Override protected void onCreate(Bundle state) { }
    @Override protected void onPause() { throw new IllegalStateException("injected pause failure"); }
    @Override protected void onStop() { System.out.println("[test] stop despite pause failure"); }
    @Override protected void onDestroy() { System.out.println("[test] destroy despite pause failure"); }
}
