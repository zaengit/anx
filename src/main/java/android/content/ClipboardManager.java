package android.content;
/** Private, in-process clipboard; no host clipboard integration. */
public class ClipboardManager {
    private ClipData primaryClip;
    public void setPrimaryClip(ClipData clip) {
        if (clip == null) throw new NullPointerException("clip");
        primaryClip = clip;
    }
    public ClipData getPrimaryClip() { return primaryClip; }
    public boolean hasPrimaryClip() { return primaryClip != null; }
}
