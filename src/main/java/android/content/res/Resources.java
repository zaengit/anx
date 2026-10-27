package android.content.res;

/** Read-only compiled string lookup for default-config `resources.arsc` entries. */
public final class Resources {
    private final AssetManager assets;
    public Resources(AssetManager assets) {
        if (assets == null) throw new NullPointerException("assets");
        this.assets = assets;
    }
    public AssetManager getAssets() { return assets; }
    public CharSequence getText(int id) { return getString(id); }
    public String getString(int id) {
        String value = CompiledStrings.find(assets.apkPathForHost(), id);
        if (value == null)
            throw new NotFoundException("String resource not found: 0x"
                    + Integer.toHexString(id));
        return value;
    }
    public static class NotFoundException extends RuntimeException {
        public NotFoundException(String message) { super(message); }
    }
}
