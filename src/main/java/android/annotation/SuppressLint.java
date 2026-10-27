package android.annotation;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;
/** Compatibility annotation; does not affect runtime behavior. */
@Retention(RetentionPolicy.CLASS)
@Target({ElementType.TYPE, ElementType.FIELD, ElementType.METHOD,
        ElementType.CONSTRUCTOR, ElementType.PARAMETER, ElementType.LOCAL_VARIABLE})
public @interface SuppressLint { String[] value(); }
