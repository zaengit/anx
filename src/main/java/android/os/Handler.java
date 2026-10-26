package android.os;
/** Handler tied to an explicitly prepared Looper. */
public class Handler {
    private final Looper looper;
    public Handler() { this(Looper.myLooper()); }
    public Handler(Looper looper) {
        if (looper == null) throw new IllegalStateException("No Looper for Handler");
        this.looper = looper;
    }
    public final Looper getLooper() { return looper; }
    public boolean post(Runnable callback) { return postDelayed(callback, 0); }
    public boolean postDelayed(Runnable callback, long delayMillis) {
        if (callback == null) throw new NullPointerException("callback");
        Message message = Message.obtain();
        message.callback = callback;
        return sendMessageDelayed(message, delayMillis);
    }
    public boolean sendEmptyMessage(int what) { return sendMessage(Message.obtain(this, what)); }
    public boolean sendMessage(Message message) { return sendMessageDelayed(message, 0); }
    public boolean sendMessageDelayed(Message message, long delayMillis) {
        if (message == null) throw new NullPointerException("message");
        if (delayMillis < 0) delayMillis = 0;
        if (message.target != null && message.target != this) {
            throw new IllegalArgumentException("Message already belongs to another Handler");
        }
        message.target = this;
        return looper.getQueue().enqueue(message, Looper.uptimeMillis() + delayMillis);
    }
    public void removeCallbacks(Runnable callback) { looper.getQueue().removeCallbacks(this, callback); }
    public void removeMessages(int what) { looper.getQueue().removeMessages(this, what); }
    public void dispatchMessage(Message message) {
        if (message.callback != null) message.callback.run();
        else handleMessage(message);
    }
    public void handleMessage(Message message) { }
}
