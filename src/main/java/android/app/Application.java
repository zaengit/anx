package android.app;
import android.content.Context;
/** One in-process Application per ANX launch; no Android system services. */
public class Application extends Context {
    public void onCreate() { }
    public void onTerminate() { }
    public final void performCreateForHost() { onCreate(); }
    public final void performTerminateForHost() { onTerminate(); }
}
