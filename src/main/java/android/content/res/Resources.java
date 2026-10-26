package android.content.res;
/** Minimal read-only resources facade; compiled resources.arsc IDs are unsupported. */
public final class Resources {
    private final AssetManager assets;
    public Resources(AssetManager assets) {
        if (assets == null) throw new NullPointerException("assets");
        this.assets = assets;
    }
    public AssetManager getAssets() { return assets; }
    public String getString(int id) {
        throw new NotFoundException("Compiled Android resource IDs are not supported: 0x"
                + Integer.toHexString(id));
    }
    public static class NotFoundException extends RuntimeException {
        public NotFoundException(String message) { super(message); }
    }
}
