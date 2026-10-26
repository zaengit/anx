package org.anx.tests;
import android.app.Application;
import android.content.Context;
import android.content.SharedPreferences;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
public final class StorageTest {
    private static void check(boolean pass, String message) {
        if (!pass) throw new AssertionError(message);
    }
    private static Application application(String name) {
        Application app = new Application();
        app.attachHostPackage(name);
        app.attachHostApplication(app);
        return app;
    }
    public static void main(String[] args) throws Exception {
        Application app = application("org.anx.fixture");
        SharedPreferences prefs = app.getSharedPreferences("settings", Context.MODE_PRIVATE);
        check(prefs.edit().clear().putString("title", "persists").putInt("count", 5)
                .putLong("timestamp", 9000000001L).putBoolean("enabled", true)
                .putFloat("scale", 1.25f).commit(), "write preferences");
        Application another = application("org.anx.fixture");
        SharedPreferences fresh = another.getSharedPreferences("settings", Context.MODE_PRIVATE);
        check("persists".equals(fresh.getString("title", null)), "string persisted");
        check(fresh.getInt("count", -1) == 5, "int persisted");
        check(fresh.getLong("timestamp", 0) == 9000000001L, "long persisted");
        check(fresh.getBoolean("enabled", false), "boolean persisted");
        check(fresh.getFloat("scale", 0) == 1.25f, "float persisted");
        check(fresh.edit().remove("title").commit(), "remove commit");
        check(!prefs.contains("title"), "removed preference");
        try (FileOutputStream out = app.openFileOutput("sample.txt", Context.MODE_PRIVATE)) {
            out.write("hello".getBytes(StandardCharsets.UTF_8));
        }
        try (FileOutputStream out = app.openFileOutput("sample.txt", Context.MODE_APPEND)) {
            out.write(" world".getBytes(StandardCharsets.UTF_8));
        }
        byte[] bytes = new byte[11];
        try (FileInputStream in = another.openFileInput("sample.txt")) {
            check(in.read(bytes) == 11, "file read");
        }
        check("hello world".equals(new String(bytes, StandardCharsets.UTF_8)), "app-local data");
        check(app.getFilesDir().isDirectory() && app.getCacheDir().isDirectory(), "directories");
        check(app.deleteFile("sample.txt"), "delete file");
        try {
            app.openFileOutput("../escape", Context.MODE_PRIVATE);
            throw new AssertionError("unsafe path accepted");
        } catch (IllegalArgumentException expected) { }
        try {
            app.getSharedPreferences("../../unsafe", Context.MODE_PRIVATE);
            throw new AssertionError("unsafe preference name accepted");
        } catch (IllegalArgumentException expected) { }
        try {
            application("../invalid");
            throw new AssertionError("unsafe package accepted");
        } catch (IllegalArgumentException expected) { }
        check(!application("org.anx.isolated").getSharedPreferences("settings",
                Context.MODE_PRIVATE).contains("count"), "isolated per package");
        System.out.println("[PASS] per-app files and persistent SharedPreferences");
    }
}
