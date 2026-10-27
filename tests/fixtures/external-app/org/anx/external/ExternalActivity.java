package org.anx.external;
import android.app.Activity;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
/** Independent Android-SDK-compiled UI test, not compiled against ANX classes. */
public final class ExternalActivity extends Activity {
    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        final TextView label = new TextView(this);
        label.setText(R.string.title_alias_chain);
        if (!"External APK from Android SDK".equals(getString(R.string.screen_title_alias)))
            throw new AssertionError("Aliased string resource mismatch");
        if (!"Selamat datang di ANX — ✓".equals(getString(R.string.utf8_probe)))
            throw new AssertionError("UTF-8 compiled string resource failed");
        System.out.println("[external] resources.arsc lookup ok");
        if (getColor(R.color.accent_alias) != 0xff336699)
            throw new AssertionError("Compiled color resource mismatch");
        if (getResources().getDimension(R.dimen.content_gap_alias) != 12f
                || getResources().getDimensionPixelSize(R.dimen.content_gap_alias) != 12)
            throw new AssertionError("Compiled dimension resource mismatch");
        System.out.println("[external] color and dimension resources ok");
        System.out.println("[external] resource references resolved");
        if (!getResources().getBoolean(R.bool.enabled_alias)
                || getResources().getBoolean(R.bool.disabled)
                || getResources().getInteger(R.integer.max_retries_alias) != 42
                || getResources().getInteger(R.integer.negative_probe) != -7)
            throw new AssertionError("Boolean or integer resource mismatch");
        if (!"Welcome, ANX! Count 3".equals(
                getString(R.string.welcome_format_alias, "ANX", 3)))
            throw new AssertionError("Formatted string resource mismatch");
        System.out.println("[external] boolean integer and formatted strings ok");
        if (!"loaded-from-classes2".equals(SecondaryDexSentinel.marker()))
            throw new AssertionError("secondary DEX helper not loaded");
        System.out.println("[external] DEX helper: " + SecondaryDexSentinel.marker());
        Button button = new Button(this);
        button.setText("Update");
        button.setOnClickListener(v -> {
            label.setText(getString(R.string.clicked_alias));
            System.out.println("[external] click updated label");
        });
        content.addView(label);
        content.addView(button);
        setContentView(content);
    }
}
