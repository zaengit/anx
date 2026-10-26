package android.content.res;
import java.io.FilterInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
/** Read-only APK assets; no Android resource-table lookup. */
public final class AssetManager {
    private final String apkPath;
    public AssetManager(String apkPath) { this.apkPath = apkPath; }
    public InputStream open(String fileName) throws IOException {
        if (fileName == null || fileName.isEmpty() || fileName.startsWith("/")
                || fileName.indexOf('\\') >= 0 || fileName.indexOf('\u0000') >= 0) {
            throw new IllegalArgumentException("Invalid asset path");
        }
        for (String part : fileName.split("/")) {
            if (part.equals(".") || part.equals("..") || part.isEmpty())
                throw new IllegalArgumentException("Invalid asset path");
        }
        if (apkPath == null) throw new FileNotFoundException("No APK attached to Context");
        final ZipFile zip = new ZipFile(apkPath);
        try {
            ZipEntry entry = zip.getEntry("assets/" + fileName);
            if (entry == null || entry.isDirectory()) throw new FileNotFoundException(fileName);
            InputStream stream = zip.getInputStream(entry);
            return new FilterInputStream(stream) {
                @Override public void close() throws IOException {
                    try { super.close(); } finally { zip.close(); }
                }
            };
        } catch (IOException | RuntimeException error) {
            zip.close();
            throw error;
        }
    }
}
