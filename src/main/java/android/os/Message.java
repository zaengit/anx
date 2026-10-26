package android.os;
/** Main-thread message. Pooling and parceling are not implemented. */
public final class Message {
    public int what;
    public int arg1;
    public int arg2;
    public Object obj;
    Handler target;
    Runnable callback;
    long when;
    long sequence;
    public static Message obtain() { return new Message(); }
    public static Message obtain(Handler target, int what) {
        Message message = obtain();
        message.target = target;
        message.what = what;
        return message;
    }
}
