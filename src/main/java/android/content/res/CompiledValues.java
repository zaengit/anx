package android.content.res;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.HashSet;
import java.util.Set;
import java.nio.charset.StandardCharsets;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/** Bounded reader of simple Android compiled resource values.
 * Only default-config, non-complex TYPE_STRING / COLOR / DIMENSION entries are supported.
 * Not an Android AssetManager implementation or full resource configuration engine.
 */
final class CompiledValues {
    private static final int MAX_TABLE = 8 * 1024 * 1024;
    private static final int MAX_STRINGS = 100_000;
    private static final int RES_TABLE = 0x0002;
    private static final int STRING_POOL = 0x0001;
    private static final int PACKAGE = 0x0200;
    private static final int TYPE = 0x0201;
    private static final int TYPE_STRING = 0x03;
    private static final int TYPE_INT_DEC = 0x10;
    private static final int TYPE_INT_HEX = 0x11;
    private static final int TYPE_INT_BOOLEAN = 0x12;
    private static final int TYPE_REFERENCE = 0x01;
    private static final int MAX_REFERENCE_DEPTH = 16;
    private static final int NO_ENTRY = -1;

    private final byte[] bytes;
    private CompiledValues(byte[] bytes) { this.bytes = bytes; }
    private static final int TYPE_DIMENSION = 0x05;

    static final class Value {
        final int type;
        final int data;
        final String[] strings;
        Value(int type, int data, String[] strings) {
            this.type = type;
            this.data = data;
            this.strings = strings;
        }
    }

    static String findString(String apkPath, int id) {
        Value v = findResolved(apkPath, id);
        return v == null || v.type != TYPE_STRING ? null : get(v.strings, v.data);
    }
    static Integer findInteger(String apkPath, int id) {
        Value v = findResolved(apkPath, id);
        return v != null && (v.type == TYPE_INT_DEC || v.type == TYPE_INT_HEX)
                ? Integer.valueOf(v.data) : null;
    }
    static Boolean findBoolean(String apkPath, int id) {
        Value v = findResolved(apkPath, id);
        return v != null && v.type == TYPE_INT_BOOLEAN
                ? Boolean.valueOf(v.data != 0) : null;
    }
    static Integer findColor(String apkPath, int id) {
        Value v = findResolved(apkPath, id);
        if (v == null || v.type < 0x1c || v.type > 0x1f) return null;
        return Integer.valueOf(v.data);
    }
    static Float findDimension(String apkPath, int id) {
        Value v = findResolved(apkPath, id);
        if (v == null || v.type != TYPE_DIMENSION) return null;
        int unit = v.data & 0x0f;
        // Fixed virtual density=1.0, scaled density=1.0 for the narrow ANX MVP.
        if (unit != 0 && unit != 1 && unit != 2) return null;
        float[] radixMultipliers = {1f / 256f, 1f / 32768f,
                1f / 8388608f, 1f / 2147483648f};
        int radix = (v.data >> 4) & 3;
        return Float.valueOf((v.data & 0xffffff00) * radixMultipliers[radix]);
    }

    private static Value findResolved(String apkPath, int id) {
        if (apkPath == null || id == 0) return null;
        try (ZipFile zip = new ZipFile(apkPath)) {
            ZipEntry entry = zip.getEntry("resources.arsc");
            if (entry == null) return null;
            if (entry.getSize() > MAX_TABLE)
                throw invalid("resources.arsc exceeds 8 MiB");
            ByteArrayOutputStream buffer = new ByteArrayOutputStream();
            try (InputStream in = zip.getInputStream(entry)) {
                byte[] chunk = new byte[16 * 1024];
                int read;
                while ((read = in.read(chunk)) != -1) {
                    if (buffer.size() + read > MAX_TABLE)
                        throw invalid("resources.arsc expanded past limit");
                    buffer.write(chunk, 0, read);
                }
            }
            CompiledValues table = new CompiledValues(buffer.toByteArray());
            int current = id;
            int packageId = id >>> 24;
            Set<Integer> visited = new HashSet<Integer>();
            for (int depth = 0; depth < MAX_REFERENCE_DEPTH; depth++) {
                if (!visited.add(Integer.valueOf(current)))
                    throw invalid("cyclic resource reference");
                Value value = table.lookup(current);
                if (value == null || value.type != TYPE_REFERENCE) return value;
                if (value.data == 0) return null;
                // Only same-package references. Framework/split/overlay lookups
                // need a complete Android resource manager, not this parser.
                if ((value.data >>> 24) != packageId) return null;
                current = value.data;
            }
            throw invalid("resource reference depth exceeds safety limit");
        } catch (IOException ex) {
            throw invalid("Cannot read compiled resources: " + ex);
        }
    }

    private static Resources.NotFoundException invalid(String why) {
        return new Resources.NotFoundException("Malformed or unsupported resources.arsc: " + why);
    }
    private void bounds(long begin, long length, long end) {
        if (begin < 0 || length < 0 || end < 0 ||
                begin + length > end || end > bytes.length)
            throw invalid("out-of-bounds resource table");
    }
    private int byteAt(int pos) {
        bounds(pos, 1, bytes.length);
        return bytes[pos] & 0xff;
    }
    private int u16(int pos) {
        bounds(pos, 2, bytes.length);
        return byteAt(pos) | byteAt(pos + 1) << 8;
    }
    private int i32(int pos) {
        bounds(pos, 4, bytes.length);
        return byteAt(pos) | byteAt(pos + 1) << 8
                | byteAt(pos + 2) << 16 | byteAt(pos + 3) << 24;
    }
    private int positive32(int pos) {
        int value = i32(pos);
        if (value < 0) throw invalid("negative/overflowed size");
        return value;
    }
    private int[] chunk(int pos, int limit) {
        bounds(pos, 8, limit);
        int headerSize = u16(pos + 2);
        int size = positive32(pos + 4);
        bounds(pos, size, limit);
        if (headerSize < 8 || size < headerSize)
            throw invalid("invalid chunk header");
        return new int[]{headerSize, size};
    }
    private int length8(int[] position, int end) {
        bounds(position[0], 1, end);
        int first = byteAt(position[0]++);
        if ((first & 0x80) == 0) return first;
        bounds(position[0], 1, end);
        return ((first & 0x7f) << 8) | byteAt(position[0]++);
    }
    private int length16(int[] position, int end) {
        bounds(position[0], 2, end);
        int first = u16(position[0]);
        position[0] += 2;
        if ((first & 0x8000) == 0) return first;
        bounds(position[0], 2, end);
        int second = u16(position[0]);
        position[0] += 2;
        return ((first & 0x7fff) << 16) | second;
    }
    private String[] stringsAt(int offset, int limit) {
        int[] c = chunk(offset, limit);
        int end = offset + c[1];
        if (u16(offset) != STRING_POOL || c[0] < 28)
            throw invalid("invalid string pool");
        int count = positive32(offset + 8);
        int styles = positive32(offset + 12);
        int flags = i32(offset + 16);
        int dataStart = positive32(offset + 20);
        if (count > MAX_STRINGS || styles > MAX_STRINGS)
            throw invalid("string count exceeds limit");
        bounds((long)offset + c[0], 4L * (count + styles), end);
        bounds((long)offset + dataStart, 0, end);
        boolean utf8 = (flags & 0x100) != 0;
        String[] strings = new String[count];
        for (int i = 0; i < count; i++) {
            int relative = positive32(offset + c[0] + 4 * i);
            int[] position = {offset + dataStart + relative};
            bounds(position[0], 1, end);
            if (utf8) {
                length8(position, end); // UTF-16 code unit count
                int encodedLength = length8(position, end);
                bounds(position[0], (long)encodedLength + 1, end);
                if (byteAt(position[0] + encodedLength) != 0)
                    throw invalid("missing UTF-8 terminator");
                strings[i] = new String(bytes, position[0], encodedLength, StandardCharsets.UTF_8);
            } else {
                int units = length16(position, end);
                bounds(position[0], (long)units * 2 + 2, end);
                if (u16(position[0] + units * 2) != 0)
                    throw invalid("missing UTF-16 terminator");
                strings[i] = new String(bytes, position[0], units * 2, StandardCharsets.UTF_16LE);
            }
        }
        return strings;
    }
    private static String get(String[] strings, int index) {
        if (index < 0 || index >= strings.length)
            throw invalid("string pool index out of bounds");
        return strings[index];
    }
    private Value lookup(int id) {
        if (bytes.length < 12 || u16(0) != RES_TABLE)
            throw invalid("invalid table signature");
        int[] root = chunk(0, bytes.length);
        if (root[0] < 12 || root[1] != bytes.length)
            throw invalid("invalid table size");
        String[] globals = null;
        int targetPkg = (id >>> 24) & 0xff;
        int targetType = (id >>> 16) & 0xff;
        int targetEntry = id & 0xffff;
        int cursor = root[0];
        while (cursor < root[1]) {
            int[] c = chunk(cursor, root[1]);
            int kind = u16(cursor);
            if (kind == STRING_POOL && globals == null) {
                globals = stringsAt(cursor, root[1]);
            } else if (kind == PACKAGE && globals != null && c[0] >= 284) {
                int pkgId = positive32(cursor + 8);
                if (pkgId == targetPkg) {
                    int typeIdOffset = c[0] >= 288 ? positive32(cursor + 284) : 0;
                    Value hit = findType(cursor, c, globals, targetType - typeIdOffset, targetEntry);
                    if (hit != null) return hit;
                }
            }
            cursor += c[1];
        }
        return null;
    }
    private Value findType(int pkgStart, int[] pkg, String[] pool,
                            int typeId, int entryIndex) {
        if (typeId <= 0 || typeId > 255) return null;
        int cursor = pkgStart + pkg[0];
        int end = pkgStart + pkg[1];
        while (cursor < end) {
            int[] c = chunk(cursor, end);
            if (u16(cursor) == TYPE && c[0] >= 24
                    && byteAt(cursor + 8) == typeId) {
                int count = positive32(cursor + 12);
                int entriesStart = positive32(cursor + 16);
                if (count > MAX_STRINGS || entryIndex >= count)
                    throw invalid("resource entry index out of range");
                bounds((long)cursor + c[0], 4L * count, cursor + c[1]);
                int configBytes = positive32(cursor + 20);
                bounds((long)cursor + 20, configBytes, cursor + c[0]);
                boolean defaultConfig = true;
                for (int i = 24; i < 20 + configBytes; i++) {
                    if (byteAt(cursor + i) != 0) { defaultConfig = false; break; }
                }
                if (defaultConfig) {
                    int relative = i32(cursor + c[0] + entryIndex * 4);
                    if (relative != NO_ENTRY) {
                        if (relative < 0) throw invalid("resource entry offset invalid");
                        long ep = (long)cursor + entriesStart + relative;
                        bounds(ep, 8, cursor + c[1]);
                        int entry = (int)ep;
                        int entrySize = u16(entry);
                        int flags = u16(entry + 2);
                        if (entrySize < 8) throw invalid("resource entry header invalid");
                        bounds(entry, (long)entrySize + 8, cursor + c[1]);
                        if ((flags & 1) == 0) {
                            int value = entry + entrySize;
                            if (u16(value) >= 8)
                                return new Value(byteAt(value + 3), i32(value + 4), pool);
                        }
                    }
                }
            }
            cursor += c[1];
        }
        return null;
    }
}
