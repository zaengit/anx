package org.anx.tests;

import android.app.Application;
import android.content.res.Resources;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** Generated malformed/recursive resources.arsc fixtures without Android SDK. */
public final class ResourceReferenceSafetyTest {
    private static void expectNotFound(Resources res, int id, String contains) {
        try {
            res.getString(id);
            throw new AssertionError("Resource unexpectedly accepted: 0x" +
                    Integer.toHexString(id));
        } catch (Resources.NotFoundException expected) {
            if (!expected.getMessage().contains(contains)) {
                throw new AssertionError("Expected " + contains + ", got " + expected, expected);
            }
        }
    }

    private static byte[] resourceTable(int[] targets) {
        int count = targets.length;
        int typeStart = 12 + 28 + 288;
        int entriesStart = 28 + count * 4;
        int chunkSize = entriesStart + count * 16;
        ByteBuffer b = ByteBuffer.allocate(typeStart + chunkSize)
                .order(ByteOrder.LITTLE_ENDIAN);
        b.putShort(0, (short)0x0002);
        b.putShort(2, (short)12);
        b.putInt(4, b.capacity());
        b.putInt(8, 1);
        b.putShort(12, (short)1);
        b.putShort(14, (short)28);
        b.putInt(16, 28);
        b.putInt(12 + 20, 28);
        int pkg = 12 + 28;
        b.putShort(pkg, (short)0x0200);
        b.putShort(pkg + 2, (short)288);
        b.putInt(pkg + 4, 288 + chunkSize);
        b.putInt(pkg + 8, 0x7f);
        b.putShort(typeStart, (short)0x0201);
        b.putShort(typeStart + 2, (short)28);
        b.putInt(typeStart + 4, chunkSize);
        b.put(typeStart + 8, (byte)1);
        b.putInt(typeStart + 12, count);
        b.putInt(typeStart + 16, entriesStart);
        b.putInt(typeStart + 20, 4); // ResTable_config size only, default
        for (int index = 0; index < count; index++) {
            b.putInt(typeStart + 28 + 4 * index, 16 * index);
            int entry = typeStart + entriesStart + 16 * index;
            b.putShort(entry, (short)8);
            b.putShort(entry + 8, (short)8);
            b.put(entry + 11, (byte)1); // TYPE_REFERENCE
            b.putInt(entry + 12, targets[index]);
        }
        return b.array();
    }

    public static void main(String[] args) throws Exception {
        int first = 0x7f010000;
        int second = 0x7f010001;
        int third = 0x7f010002;
        File zip = File.createTempFile("anx-recursive-resources-", ".apk");
        zip.deleteOnExit();
        try (ZipOutputStream out = new ZipOutputStream(new FileOutputStream(zip))) {
            out.putNextEntry(new ZipEntry("resources.arsc"));
            out.write(resourceTable(new int[]{second, first, 0x01010005}));
            out.closeEntry();
        }
        Application app = new Application();
        app.attachHostApk(zip.getAbsolutePath());
        Resources res = app.getResources();
        expectNotFound(res, first, "cyclic");
        expectNotFound(res, third, "not found"); // no framework table
        expectNotFound(res, 0x7f0100ff, "out of range");
        System.out.println("[PASS] Cyclic and cross-package resource references rejected");
    }
}
