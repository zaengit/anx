package android.util;
import java.io.PrintWriter;
import java.io.StringWriter;
/** Logcat-style Java console adapter; logcat filtering/buffers are not provided. */
public final class Log {
    public static final int VERBOSE = 2;
    public static final int DEBUG = 3;
    public static final int INFO = 4;
    public static final int WARN = 5;
    public static final int ERROR = 6;
    public static final int ASSERT = 7;
    private Log() { }
    public static int v(String tag, String message) { return println(VERBOSE, tag, message); }
    public static int d(String tag, String message) { return println(DEBUG, tag, message); }
    public static int i(String tag, String message) { return println(INFO, tag, message); }
    public static int w(String tag, String message) { return println(WARN, tag, message); }
    public static int e(String tag, String message) { return println(ERROR, tag, message); }
    public static int wtf(String tag, String message) { return println(ASSERT, tag, message); }
    public static int v(String tag, String message, Throwable error) {
        return println(VERBOSE, tag, message + "\n" + getStackTraceString(error));
    }
    public static int d(String tag, String message, Throwable error) {
        return println(DEBUG, tag, message + "\n" + getStackTraceString(error));
    }
    public static int i(String tag, String message, Throwable error) {
        return println(INFO, tag, message + "\n" + getStackTraceString(error));
    }
    public static int w(String tag, String message, Throwable error) {
        return println(WARN, tag, message + "\n" + getStackTraceString(error));
    }
    public static int e(String tag, String message, Throwable error) {
        return println(ERROR, tag, message + "\n" + getStackTraceString(error));
    }
    public static boolean isLoggable(String tag, int priority) {
        return priority >= VERBOSE && priority <= ASSERT;
    }
    public static String getStackTraceString(Throwable error) {
        if (error == null) return "";
        StringWriter result = new StringWriter();
        PrintWriter out = new PrintWriter(result);
        error.printStackTrace(out);
        out.flush();
        return result.toString();
    }
    public static int println(int priority, String tag, String message) {
        if (priority < VERBOSE || priority > ASSERT)
            throw new IllegalArgumentException("Unknown log priority " + priority);
        String level = priority == VERBOSE ? "VERBOSE"
                : priority == DEBUG ? "DEBUG" : priority == INFO ? "INFO"
                : priority == WARN ? "WARN" : priority == ERROR ? "ERROR" : "ASSERT";
        String output = "[android/" + level + "] "
                + (tag == null ? "(null)" : tag) + ": "
                + (message == null ? "null" : message);
        if (priority >= WARN) System.err.println(output);
        else System.out.println(output);
        return message == null ? 4 : message.length();
    }
}
