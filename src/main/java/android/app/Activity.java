package android.app;

import android.content.Context;
import android.os.Bundle;
import android.view.View;

/** API kompatibilitas parsial dan lifecycle tanpa ActivityManager Android. */
public class Activity extends Context {
    private View contentView;

    protected void onCreate(Bundle state) { }
    protected void onStart() { }
    protected void onResume() { }
    protected void onPause() { }
    protected void onStop() { }
    protected void onDestroy() { }

    public final void setContentView(View view) { this.contentView = view; }
    public final View getContentViewForHost() { return contentView; }

    /** Dispatch internal oleh launcher. */
    public final void performCreate(Bundle b) { onCreate(b); }
    public final void performStart() { onStart(); }
    public final void performResume() { onResume(); }
    public final void performPause() { onPause(); }
    public final void performStop() { onStop(); }
    public final void performDestroy() { onDestroy(); }
}
