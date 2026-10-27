package android.os;
/** A clearly synthetic compatibility profile; not the real Android OS. */
public final class Build {
    private Build() { }
    public static final String SERIAL = "ANX-UNAVAILABLE";
    public static final class VERSION {
        private VERSION() { }
        public static final int SDK_INT = 26;
        public static final String RELEASE = "ANX-host-compatibility";
    }
    public static final class VERSION_CODES {
        private VERSION_CODES() { }
        public static final int HONEYCOMB = 11;
        public static final int O = 26;
    }
}
