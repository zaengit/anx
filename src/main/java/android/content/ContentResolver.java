package android.content;
/** Host metadata accessor, not an Android provider/database implementation. */
public class ContentResolver {
    private final Context context;
    public ContentResolver(Context context) {
        if (context == null) throw new NullPointerException("context");
        this.context = context;
    }
    public final Context getHostContext() { return context; }
}
