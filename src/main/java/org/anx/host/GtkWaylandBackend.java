package org.anx.host;
import android.os.Looper;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
/** External native GTK4/GDK Wayland process; events dispatch on the ART main thread. */
public final class GtkWaylandBackend implements WindowBackend {
    private static final class Content {
        TextView label;
        Button button;
    }
    private Content model(View view) {
        Content result = new Content();
        if (view instanceof LinearLayout) {
            LinearLayout layout = (LinearLayout) view;
            if (layout.getOrientation() != LinearLayout.VERTICAL)
                throw new UnsupportedOperationException("Only vertical LinearLayout is supported");
            if (layout.getChildCount() > 2)
                throw new UnsupportedOperationException("At most one TextView and one Button are supported");
            for (View child : layout.getChildrenForHost()) collect(result, child);
        } else {
            collect(result, view);
        }
        if (result.label == null) throw new UnsupportedOperationException("A TextView is required");
        return result;
    }
    private static void collect(Content result, View child) {
        if (child instanceof Button && result.button == null) result.button = (Button) child;
        else if (child instanceof TextView && !(child instanceof Button) && result.label == null)
            result.label = (TextView) child;
        else throw new UnsupportedOperationException("Unsupported GUI view tree");
    }
    @Override public void show(View view) {
        Content content = model(view);
        String binary = System.getenv("ANX_WAYLAND_BINARY");
        if (binary == null || binary.isEmpty()) binary = "anx-wayland";
        Process process = null;
        try {
            ProcessBuilder builder = new ProcessBuilder(binary,
                    "ANX: " + view.getContext().getPackageName(),
                    content.label.getText().toString(),
                    content.button == null ? "" : content.button.getText().toString());
            builder.environment().put("GDK_BACKEND", "wayland");
            builder.redirectError(ProcessBuilder.Redirect.INHERIT);
            process = builder.start();
            BufferedReader input = new BufferedReader(new InputStreamReader(
                    process.getInputStream(), StandardCharsets.UTF_8));
            BufferedWriter output = new BufferedWriter(new OutputStreamWriter(
                    process.getOutputStream(), StandardCharsets.UTF_8));
            boolean ready = false;
            boolean closed = false;
            boolean clicked = false;
            boolean updated = false;
            String line;
            while ((line = input.readLine()) != null) {
                if ("READY".equals(line)) {
                    ready = true;
                    System.out.println("[anx-wayland] window ready");
                } else if ("CLICK".equals(line)) {
                    if (!ready || content.button == null) throw new IOException("Unexpected click event");
                    clicked = true;
                    content.button.performClick();
                    Looper.myLooper().drainForHost();
                    String encoded = Base64.getEncoder().encodeToString(
                            content.label.getText().toString().getBytes(StandardCharsets.UTF_8));
                    output.write("TEXT\t" + encoded + "\n");
                    output.flush();
                    System.out.println("[anx-wayland] button clicked");
                } else if ("UPDATED".equals(line)) {
                    if (!clicked || !ready) throw new IOException("Unexpected repaint acknowledgement");
                    updated = true;
                    System.out.println("[anx-wayland] label updated");
                } else if ("CLOSE".equals(line)) {
                    closed = true;
                    break;
                } else throw new IOException("Invalid Wayland backend message: " + line);
            }
            if (process.waitFor() != 0) throw new IOException("Wayland backend failed");
            if (!ready || !closed) throw new IOException("Wayland backend ended without READY/CLOSE");
            if ("1".equals(System.getenv("ANX_GUI_TEST_AUTOCLICK")) && (!clicked || !updated))
                throw new IOException("Wayland integration test did not click and repaint");
            System.out.println("[anx-wayland] window closed");
        } catch (IOException error) {
            throw new IllegalStateException("Wayland window unavailable: " + error.getMessage(), error);
        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Wayland backend interrupted", error);
        } finally {
            if (process != null) process.destroy();
        }
    }
}
