package android.app;
import android.content.Context;
import android.content.Intent;
import android.content.res.CompiledLayout;
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
    /** Default-config binary XML layout subset; not a general LayoutInflater. */
    public void setContentView(int layoutId) {
        contentView = CompiledLayout.inflate(this, layoutId);
    }
    @SuppressWarnings("unchecked")
    public <T extends View> T findViewById(int id) {
        return contentView == null ? null : (T) contentView.findViewById(id);
    }
    public final View getContentViewForHost() { return contentView; }
    public final void performCreate(Bundle b) { onCreate(b); }
    public final void performStart() { onStart(); }
    public final void performResume() { onResume(); }
    public final void performPause() { onPause(); }
    public final void performStop() { onStop(); }
    public final void performDestroy() { onDestroy(); }
}
