package android.text;
/** Legacy interface wrapper for SDK-compiled, backwards-compatible APKs. */
@Deprecated
public class ClipboardManager extends android.content.ClipboardManager {
    @Deprecated public void setText(CharSequence text) {
        setPrimaryClip(android.content.ClipData.newPlainText("", text));
    }
    @Deprecated public CharSequence getText() {
        android.content.ClipData clip = getPrimaryClip();
        return clip == null ? null : clip.getItemAt(0).getText();
    }
}
