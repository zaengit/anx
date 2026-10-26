package android.app;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
/** Lifecycle subset executed by ANX's Instrumentation on the prepared main thread. */
public class Activity extends Context {
    private View contentView;
    private Intent intent;
    protected void onCreate(Bundle state) { }
    protected void onStart() { }
    protected void onResume() { }
    protected void onPause() { }
    protected void onStop() { }
    protected void onDestroy() { }
    public final Application getApplication() { return (Application) getApplicationContext(); }
    public final Intent getIntent() { return intent; }
    public final void attachHostIntent(Intent value) { intent = value; }
    public final void setContentView(View view) { contentView = view; }
    public final View getContentViewForHost() { return contentView; }
    public final void performCreate(Bundle b) { onCreate(b); }
    public final void performStart() { onStart(); }
    public final void performResume() { onResume(); }
    public final void performPause() { onPause(); }
    public final void performStop() { onStop(); }
    public final void performDestroy() { onDestroy(); }
}
