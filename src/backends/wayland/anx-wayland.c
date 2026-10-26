#define _POSIX_C_SOURCE 200809L
#include <gtk/gtk.h>
#include <glib-unix.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
typedef struct {
    GtkApplication *app;
    GtkWidget *label;
    GtkWidget *window;
    GtkWidget *button;
    gboolean test_autoclick;
    const char *title;
    const char *initial_label;
    const char *button_label;
    GString *input;
    gboolean closing;
} HostWindow;

static void announce(HostWindow *state, const char *event) {
    (void)state;
    fputs(event, stdout);
    fputc('\n', stdout);
    fflush(stdout);
}
static void on_button_clicked(GtkButton *button, gpointer user_data) {
    (void)button;
    announce((HostWindow *)user_data, "CLICK");
}
static gboolean on_window_close(GtkWindow *window, gpointer user_data) {
    (void)window;
    HostWindow *state = user_data;
    if (!state->closing) {
        state->closing = TRUE;
        announce(state, "CLOSE");
    }
    return FALSE;
}
static gboolean click_for_test(gpointer user_data) {
    HostWindow *state = user_data;
    if (state->button != NULL && !state->closing)
        g_signal_emit_by_name(state->button, "clicked");
    return G_SOURCE_REMOVE;
}
static gboolean consume_line(HostWindow *state, const char *line) {
    if (!g_str_has_prefix(line, "TEXT\t")) return FALSE;
    const char *payload = line + 5;
    gsize length = 0;
    guchar *decoded = g_base64_decode(payload, &length);
    gboolean valid = decoded != NULL && length <= 16384
        && g_utf8_validate((const char *)decoded, (gssize)length, NULL);
    if (valid && state->label != NULL) {
        char *text = g_strndup((const char *)decoded, length);
        gtk_label_set_text(GTK_LABEL(state->label), text);
        if (state->test_autoclick) {
            /* Test verifies GTK's live label, not only the outgoing Java payload. */
            if (g_strcmp0(gtk_label_get_text(GTK_LABEL(state->label)), text) != 0) {
                g_free(text);
                g_free(decoded);
                return FALSE;
            }
            announce(state, "UPDATED");
            gtk_window_close(GTK_WINDOW(state->window));
        }
        g_free(text);
    }
    g_free(decoded);
    return valid;
}
static gboolean on_stdin_readable(gint fd, GIOCondition condition, gpointer user_data) {
    HostWindow *state = user_data;
    char buf[2048];
    if (condition & (G_IO_ERR | G_IO_NVAL)) goto end_session;
    ssize_t count = read(fd, buf, sizeof(buf));
    if (count <= 0) goto end_session;
    g_string_append_len(state->input, buf, (gssize)count);
    if (state->input->len > 32768) goto end_session;
    for (;;) {
        char *newline = memchr(state->input->str, '\n', state->input->len);
        if (newline == NULL) break;
        gsize size = (gsize)(newline - state->input->str);
        char *line = g_strndup(state->input->str, size);
        gboolean accepted = consume_line(state, line);
        g_free(line);
        g_string_erase(state->input, 0, size + 1);
        if (!accepted) goto end_session;
    }
    return G_SOURCE_CONTINUE;
end_session:
    if (!state->closing) {
        state->closing = TRUE;
        announce(state, "CLOSE");
    }
    g_application_quit(G_APPLICATION(state->app));
    return G_SOURCE_REMOVE;
}
static void on_activate(GtkApplication *app, gpointer user_data) {
    HostWindow *state = user_data;
    GtkWidget *window = gtk_application_window_new(app);
    state->window = window;
    gtk_window_set_title(GTK_WINDOW(window), state->title);
    gtk_window_set_default_size(GTK_WINDOW(window), 480, 220);
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 18);
    gtk_widget_set_margin_top(box, 24);
    gtk_widget_set_margin_bottom(box, 24);
    gtk_widget_set_margin_start(box, 24);
    gtk_widget_set_margin_end(box, 24);
    state->label = gtk_label_new(state->initial_label);
    gtk_label_set_wrap(GTK_LABEL(state->label), TRUE);
    gtk_label_set_xalign(GTK_LABEL(state->label), 0.0f);
    gtk_box_append(GTK_BOX(box), state->label);
    if (state->button_label[0] != '\0') {
        GtkWidget *button = gtk_button_new_with_label(state->button_label);
        state->button = button;
        g_signal_connect(button, "clicked", G_CALLBACK(on_button_clicked), state);
        gtk_box_append(GTK_BOX(box), button);
    }
    gtk_window_set_child(GTK_WINDOW(window), box);
    g_signal_connect(window, "close-request", G_CALLBACK(on_window_close), state);
    g_unix_fd_add(STDIN_FILENO, G_IO_IN | G_IO_HUP | G_IO_ERR | G_IO_NVAL,
                  on_stdin_readable, state);
    gtk_window_present(GTK_WINDOW(window));
    announce(state, "READY");
    /* CI-only: exercise a real, realized GTK button signal under Weston. */
    if (state->test_autoclick && state->button != NULL)
        g_timeout_add(300, click_for_test, state);
}
int main(int argc, char **argv) {
    if (argc != 4) {
        fputs("Usage: anx-wayland <title> <label> <button-label-or-empty>\n", stderr);
        return 2;
    }
    /* Do not silently switch to X11 or a non-native backend. */
    g_setenv("GDK_BACKEND", "wayland", TRUE);
    HostWindow state = {0};
    state.title = argv[1];
    state.initial_label = argv[2];
    state.button_label = argv[3];
    state.input = g_string_new(NULL);
    state.test_autoclick = g_strcmp0(g_getenv("ANX_GUI_TEST_AUTOCLICK"), "1") == 0;
    state.app = gtk_application_new("org.anx.wayland", G_APPLICATION_NON_UNIQUE);
    g_signal_connect(state.app, "activate", G_CALLBACK(on_activate), &state);
    int status = g_application_run(G_APPLICATION(state.app), 0, NULL);
    if (!state.closing) announce(&state, "CLOSE");
    g_object_unref(state.app);
    g_string_free(state.input, TRUE);
    return status;
}
