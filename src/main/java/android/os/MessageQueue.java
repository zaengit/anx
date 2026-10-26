package android.os;
import java.util.Comparator;
import java.util.PriorityQueue;
/** Time-ordered queue. Equal-time messages retain FIFO ordering. */
public final class MessageQueue {
    private final PriorityQueue<Message> messages = new PriorityQueue<>(11, new Comparator<Message>() {
        @Override public int compare(Message a, Message b) {
            if (a.when < b.when) return -1;
            if (a.when > b.when) return 1;
            return a.sequence < b.sequence ? -1 : (a.sequence == b.sequence ? 0 : 1);
        }
    });
    private boolean quitting;
    private long sequence;
    synchronized boolean enqueue(Message message, long when) {
        if (quitting) return false;
        message.when = when;
        message.sequence = sequence++;
        messages.add(message);
        notifyAll();
        return true;
    }
    synchronized Message pollDue(long now) {
        if (quitting || messages.isEmpty() || messages.peek().when > now) return null;
        return messages.remove();
    }
    synchronized Message next() {
        for (;;) {
            if (quitting) return null;
            Message first = messages.peek();
            long delay = first == null ? 0 : first.when - Looper.uptimeMillis();
            if (first != null && delay <= 0) return messages.remove();
            try { wait(first == null ? 0 : delay); }
            catch (InterruptedException ignored) { /* Wake and re-check queue state. */ }
        }
    }
    synchronized void removeCallbacks(Handler target, Runnable callback) {
        messages.removeIf(message -> message.target == target && message.callback == callback);
    }
    synchronized void removeMessages(Handler target, int what) {
        messages.removeIf(message -> message.target == target && message.callback == null && message.what == what);
    }
    public synchronized void quit() {
        quitting = true;
        messages.clear();
        notifyAll();
    }
}
