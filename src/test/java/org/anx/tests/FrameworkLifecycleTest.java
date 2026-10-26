package org.anx.tests;
import android.app.Activity;
import android.app.Application;
import android.app.Instrumentation;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.Message;
import android.widget.Button;
import android.widget.TextView;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
public final class FrameworkLifecycleTest {
    public static final class DemoApplication extends Application {
        @Override public void onCreate() { events.add("application"); }
    }
    public static final class DemoActivity extends Activity {
        @Override protected void onCreate(Bundle state) {
            events.add("create");
            check(getApplication() instanceof DemoApplication, "application bound");
            check("test.pkg".equals(getPackageName()), "package propagated");
            check("value".equals(getIntent().getStringExtra("extra")), "intent extras");
            final TextView label = new TextView(this);
            label.setText("before");
            Button button = new Button(this);
            button.setText("click");
            button.setOnClickListener(v -> label.setText("after"));
            check(button.performClick(), "click callback");
            check("after".contentEquals(label.getText()), "clicked text");
            setContentView(label);
            Handler handler = new Handler();
            Runnable removed = () -> events.add("removed");
            handler.post(removed);
            handler.removeCallbacks(removed);
            handler.post(() -> events.add("posted"));
            handler.sendEmptyMessage(7);
            Handler other = new Handler() {
                @Override public void handleMessage(Message message) {
                    events.add("message:" + message.what);
                }
            };
            other.sendEmptyMessage(9);
            check(Looper.myLooper() == Looper.getMainLooper(), "main thread");
        }
        @Override protected void onStart() { events.add("start"); }
        @Override protected void onResume() { events.add("resume"); }
        @Override protected void onPause() { events.add("pause"); }
        @Override protected void onStop() { events.add("stop"); }
        @Override protected void onDestroy() { events.add("destroy"); }
    }
    private static final List<String> events = new ArrayList<>();
    private static void check(boolean ok, String message) {
        if (!ok) throw new AssertionError(message);
    }
    public static void main(String[] args) throws Exception {
        Bundle bag = new Bundle();
        bag.putString("name", "a");
        bag.putInt("count", 4);
        bag.putBoolean("enabled", true);
        check(bag.getInt("count") == 4 && bag.getBoolean("enabled"), "bundle types");
        check("a".equals(new Bundle(bag).getString("name")), "bundle copy");
        Looper.prepareMainLooper();
        Instrumentation instrumentation = new Instrumentation();
        Application app = instrumentation.newApplication(DemoApplication.class.getName(), "test.pkg");
        instrumentation.callApplicationOnCreate(app);
        Intent intent = new Intent(Intent.ACTION_MAIN).setClassName("test.pkg", DemoActivity.class.getName())
                .addCategory(Intent.CATEGORY_LAUNCHER).putExtra("extra", "value");
        check(intent.hasCategory(Intent.CATEGORY_LAUNCHER), "intent category");
        Activity activity = instrumentation.newActivity(DemoActivity.class.getName(), app, intent);
        instrumentation.callActivityOnCreate(activity, new Bundle());
        instrumentation.callActivityOnStart(activity);
        instrumentation.callActivityOnResume(activity);
        Looper.getMainLooper().drainForHost();
        instrumentation.callActivityOnPause(activity);
        instrumentation.callActivityOnStop(activity);
        instrumentation.callActivityOnDestroy(activity);
        List<String> expected = Arrays.asList("application", "create", "start", "resume",
                "posted", "message:9", "pause", "stop", "destroy");
        check(expected.equals(events), "event order: " + events);
        Looper.getMainLooper().quit();
        check(!new Handler(Looper.getMainLooper()).post(() -> {}), "quit blocks enqueues");
        System.out.println("[PASS] M3 lifecycle, main Looper, Handler, Intent, Bundle and Button");
    }
}
