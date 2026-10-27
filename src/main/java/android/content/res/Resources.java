package android.content.res;

/** Limited default-config Android compiled resource lookup. */
public final class Resources {
    private final AssetManager assets;
    public Resources(AssetManager assets) {
        if (assets == null) throw new NullPointerException("assets");
        this.assets = assets;
    }
    public AssetManager getAssets() { return assets; }
    public CharSequence getText(int id) { return getString(id); }
    public String getString(int id) {
        String value = CompiledValues.findString(assets.apkPathForHost(), id);
        if (value == null)
            throw new NotFoundException("String resource not found: 0x"
                    + Integer.toHexString(id));
        return value;
    }
    public int getColor(int id) {
        Integer value = CompiledValues.findColor(assets.apkPathForHost(), id);
        if (value == null)
            throw new NotFoundException("Color resource not found: 0x"
                    + Integer.toHexString(id));
        return value.intValue();
    }
    public float getDimension(int id) {
        Float value = CompiledValues.findDimension(assets.apkPathForHost(), id);
        if (value == null)
            throw new NotFoundException("Dimension resource not found: 0x"
                    + Integer.toHexString(id));
        return value.floatValue();
    }
    public int getDimensionPixelSize(int id) {
        float dimension = getDimension(id);
        int rounded = Math.round(dimension);
        if (rounded != 0) return rounded;
        return dimension > 0 ? 1 : dimension < 0 ? -1 : 0;
    }
    public static class NotFoundException extends RuntimeException {
        public NotFoundException(String message) { super(message); }
    }
}
