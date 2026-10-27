package android.content.res;

import android.content.Context;
import android.view.View;
import android.widget.TextView;
import android.widget.Button;
import android.widget.LinearLayout;
import android.view.ViewGroup;
import java.util.ArrayList;
import java.util.List;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/**
 * Bounded Android binary XML inflater subset: single TextView or vertical
 * LinearLayout with nested vertical LinearLayouts, TextViews and Buttons.
 * No Android measurement, styling, framework themes or general layout support.
 */
public final class CompiledLayout {
    private static final int XML = 0x0003, STRING_POOL = 0x0001;
    private static final int START = 0x0102, END = 0x0103;
    private static final int TYPE_REFERENCE = 0x01, TYPE_STRING = 0x03;
    private static final int LIMIT = 1024 * 1024, MAX_STRINGS = 8192;
    private static final String ANDROID_NS = "http://schemas.android.com/apk/res/android";
    private final byte[] data;
    private CompiledLayout(byte[] bytes) { data = bytes; }

    public static View inflate(Context context, int layoutId) {
        if (context == null) throw new NullPointerException("context");
        String path = context.getResources().layoutPathForHost(layoutId);
        String apk = context.getAssets().apkPathForHost();
        if (apk == null) throw unsupported("No APK attached");
        try (ZipFile archive = new ZipFile(apk)) {
            ZipEntry entry = archive.getEntry(path);
            if (entry == null || entry.isDirectory())
                throw unsupported("Missing compiled layout: " + path);
            if (entry.getSize() > LIMIT) throw unsupported("Layout exceeds 1 MiB");
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            try (InputStream in = archive.getInputStream(entry)) {
                byte[] buf = new byte[8192];
                int n;
                while ((n = in.read(buf)) != -1) {
                    if (out.size() + n > LIMIT) throw unsupported("Layout exceeds 1 MiB");
                    out.write(buf, 0, n);
                }
            }
            return new CompiledLayout(out.toByteArray()).parse(context);
        } catch (IOException ex) {
            throw unsupported("Cannot read binary layout: " + ex);
        }
    }

    private static Resources.NotFoundException unsupported(String message) {
        return new Resources.NotFoundException("Unsupported compiled layout: " + message);
    }
    private void require(long pos, long size, int bound) {
        if (pos < 0 || size < 0 || pos + size > bound || bound > data.length)
            throw unsupported("truncated/out-of-bounds XML");
    }
    private int u8(int p) { require(p, 1, data.length); return data[p] & 255; }
    private int u16(int p) { require(p, 2, data.length); return u8(p) | u8(p+1)<<8; }
    private int i32(int p) {
        require(p, 4, data.length);
        return u8(p) | u8(p+1)<<8 | u8(p+2)<<16 | u8(p+3)<<24;
    }
    private int number(int p) {
        int n = i32(p);
        if (n < 0) throw unsupported("overflowed XML length");
        return n;
    }
    private int[] chunk(int p, int end) {
        require(p, 8, end);
        int header = u16(p+2), size = number(p+4);
        if (header < 8 || size < header) throw unsupported("invalid chunk header");
        require(p, size, end);
        return new int[]{header, size};
    }
    private int len8(int[] cursor, int end) {
        require(cursor[0], 1, end);
        int n = u8(cursor[0]++);
        if ((n & 128) == 0) return n;
        require(cursor[0], 1, end);
        return ((n & 127) << 8) | u8(cursor[0]++);
    }
    private int len16(int[] cursor, int end) {
        require(cursor[0], 2, end);
        int n = u16(cursor[0]); cursor[0] += 2;
        if ((n & 0x8000) == 0) return n;
        require(cursor[0], 2, end);
        int next = u16(cursor[0]); cursor[0] += 2;
        return ((n & 0x7fff) << 16) | next;
    }
    private String[] pool(int pos, int end) {
        int[] c = chunk(pos, end);
        if (u16(pos) != STRING_POOL || c[0] < 28)
            throw unsupported("missing string pool");
        int count = number(pos + 8), styles = number(pos + 12);
        int flags = i32(pos + 16), dataStart = number(pos + 20);
        if (count > MAX_STRINGS || styles > MAX_STRINGS)
            throw unsupported("excessive strings/styles");
        int chunkEnd = pos + c[1];
        require((long)pos + c[0], 4L * (count + styles), chunkEnd);
        require((long)pos + dataStart, 0, chunkEnd);
        boolean utf8 = (flags & 0x100) != 0;
        String[] values = new String[count];
        for (int i=0; i<count; i++) {
            int off = number(pos + c[0] + i*4);
            int[] at = {pos + dataStart + off};
            require(at[0], 1, chunkEnd);
            if (utf8) {
                len8(at, chunkEnd);
                int size = len8(at, chunkEnd);
                require(at[0], (long)size + 1, chunkEnd);
                if (u8(at[0] + size) != 0) throw unsupported("UTF8 terminator missing");
                values[i] = new String(data, at[0], size, StandardCharsets.UTF_8);
            } else {
                int units = len16(at, chunkEnd);
                require(at[0], (long)units*2 + 2, chunkEnd);
                if (u16(at[0] + units*2) != 0) throw unsupported("UTF16 terminator missing");
                values[i] = new String(data, at[0], units*2, StandardCharsets.UTF_16LE);
            }
        }
        return values;
    }
    private static String string(String[] values, int index) {
        if (index == -1) return null;
        if (index < 0 || index >= values.length) throw unsupported("invalid string index");
        return values[index];
    }
    private static final int TYPE_INT_DEC = 0x10;
    private static final int MAX_NODES = 16, MAX_DEPTH = 4;

    private static final class Node {
        final String tag;
        final View view;
        Node(String tag, View view) { this.tag = tag; this.view = view; }
    }

    private View parse(Context context) {
        if (data.length < 8 || u16(0) != XML) throw unsupported("not binary XML");
        int[] root = chunk(0, data.length);
        if (root[1] != data.length) throw unsupported("incorrect XML file length");
        int off = root[0], seen = 0;
        String[] strings = null;
        View rootView = null;
        List<Node> stack = new ArrayList<Node>();
        while (off < root[1]) {
            int[] c = chunk(off, root[1]);
            int kind = u16(off);
            if (kind == STRING_POOL) {
                if (strings != null) throw unsupported("duplicate string pool");
                strings = pool(off, root[1]);
            } else if (kind == START) {
                if (strings == null || c[0] < 16 || c[1] < c[0] + 20)
                    throw unsupported("bad start element");
                if (++seen > MAX_NODES || stack.size() >= MAX_DEPTH)
                    throw unsupported("view count/depth exceeds limit");
                int ext = off + c[0];
                String tag = string(strings, i32(ext + 4));
                View view;
                if ("TextView".equals(tag) || "android.widget.TextView".equals(tag))
                    view = new TextView(context);
                else if ("Button".equals(tag) || "android.widget.Button".equals(tag))
                    view = new Button(context);
                else if ("LinearLayout".equals(tag) || "android.widget.LinearLayout".equals(tag))
                    view = new LinearLayout(context);
                else throw unsupported("unsupported view type: " + tag);
                int attrOff = u16(ext + 8), attrSize = u16(ext + 10);
                int count = u16(ext + 12);
                long firstAttr = (long)ext + attrOff;
                if (attrSize < 20 || count > 256) throw unsupported("attribute bounds");
                require(firstAttr, (long)attrSize * count, off + c[1]);
                for (int a = 0; a < count; a++) {
                    int p = (int)(firstAttr + (long)a * attrSize);
                    String ns = string(strings, i32(p));
                    String name = string(strings, i32(p + 4));
                    if (!ANDROID_NS.equals(ns)) continue;
                    if (u16(p + 12) < 8) throw unsupported("invalid Android attribute");
                    int type = u8(p + 15), value = i32(p + 16);
                    if ("id".equals(name)) {
                        if (type != TYPE_REFERENCE || value == 0)
                            throw unsupported("invalid android:id");
                        view.setId(value);
                    } else if ("text".equals(name) && view instanceof TextView) {
                        TextView label = (TextView)view;
                        if (type == TYPE_REFERENCE) label.setText(context.getString(value));
                        else if (type == TYPE_STRING) label.setText(string(strings, value));
                        else throw unsupported("unsupported android:text type");
                    } else if ("orientation".equals(name) && view instanceof LinearLayout) {
                        if (type != TYPE_INT_DEC || value != LinearLayout.VERTICAL)
                            throw unsupported("only vertical LinearLayout supported");
                        ((LinearLayout)view).setOrientation(value);
                    }
                }
                if (stack.isEmpty()) {
                    if (rootView != null) throw unsupported("multiple XML roots");
                    rootView = view;
                } else {
                    View parent = stack.get(stack.size()-1).view;
                    if (!(parent instanceof LinearLayout))
                        throw unsupported("nested child requires LinearLayout");
                    ((LinearLayout)parent).addView(view);
                }
                stack.add(new Node(tag, view));
            } else if (kind == END) {
                if (stack.isEmpty() || strings == null || c[0] < 16 || c[1] < c[0] + 8)
                    throw unsupported("unbalanced end tag");
                String tag = string(strings, i32(off + c[0] + 4));
                Node node = stack.remove(stack.size()-1);
                if (!node.tag.equals(tag)) throw unsupported("mismatched XML closing tag");
            }
            off += c[1];
        }
        if (off != root[1] || strings == null || rootView == null || !stack.isEmpty())
            throw unsupported("incomplete XML tree");
        return rootView;
    }
}
