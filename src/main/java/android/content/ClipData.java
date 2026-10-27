package android.content;
/** In-memory plain text clip; does not access the host OS clipboard. */
public final class ClipData {
    private final CharSequence label;
    private final CharSequence text;
    private ClipData(CharSequence label, CharSequence text) {
        this.label = label;
        this.text = text;
    }
    public static ClipData newPlainText(CharSequence label, CharSequence text) {
        return new ClipData(label, text);
    }
    public int getItemCount() { return 1; }
    public Item getItemAt(int index) {
        if (index != 0) throw new IndexOutOfBoundsException("clip item");
        return new Item(text);
    }
    public CharSequence getDescriptionLabelForHost() { return label; }
    public static final class Item {
        private final CharSequence text;
        Item(CharSequence text) { this.text = text; }
        public CharSequence getText() { return text; }
    }
}
