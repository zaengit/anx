package android.os;
/** Single-thread event loop; the host can drain immediate work before teardown. */
public final class Looper {
    private static final ThreadLocal<Looper> LOCAL = new ThreadLocal<>();
    private static volatile Looper mainLooper;
    private final Thread owner;
    private final MessageQueue queue = new MessageQueue();
    private Looper() { owner = Thread.currentThread(); }
    public static void prepare() {
        if (LOCAL.get() != null) throw new RuntimeException("Only one Looper per thread");
        LOCAL.set(new Looper());
    }
    public static void prepareMainLooper() {
        prepare();
        synchronized (Looper.class) {
            if (mainLooper != null) throw new IllegalStateException("Main Looper already prepared");
            mainLooper = myLooper();
        }
    }
    public static Looper myLooper() { return LOCAL.get(); }
    public static Looper getMainLooper() { return mainLooper; }
    public Thread getThread() { return owner; }
    public MessageQueue getQueue() { return queue; }
    static long uptimeMillis() { return System.nanoTime() / 1000000L; }
    public static void loop() {
        Looper self = myLooper();
        if (self == null) throw new IllegalStateException("Call Looper.prepare() first");
        Message message;
        while ((message = self.queue.next()) != null) message.target.dispatchMessage(message);
    }
    /** ANX host-only: run due messages without blocking on future timers. */
    public void drainForHost() {
        if (Thread.currentThread() != owner) throw new IllegalStateException("Looper thread required");
        Message message;
        int dispatched = 0;
        while ((message = queue.pollDue(uptimeMillis())) != null) {
            if (++dispatched > 10000) throw new IllegalStateException("Too many main-thread callbacks");
            message.target.dispatchMessage(message);
        }
    }
    public void quit() { queue.quit(); }
}
