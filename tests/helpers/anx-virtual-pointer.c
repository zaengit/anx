#define _POSIX_C_SOURCE 200809L
#include <wayland-client.h>
#include <wayland-client-protocol.h>
#include "wlr-virtual-pointer-unstable-v1-client-protocol.h"
#include <linux/input-event-codes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* CI-only persistent wlroots virtual pointer; never point at user's desktop. */
static struct zwlr_virtual_pointer_manager_v1 *manager;
static struct wl_seat *seat;

static void on_global(void *data, struct wl_registry *registry, uint32_t name,
                      const char *interface, uint32_t version) {
    (void)data;
    if (strcmp(interface, zwlr_virtual_pointer_manager_v1_interface.name) == 0) {
        manager = wl_registry_bind(registry, name,
                    &zwlr_virtual_pointer_manager_v1_interface, version < 2 ? version : 2);
    } else if (strcmp(interface, wl_seat_interface.name) == 0) {
        seat = wl_registry_bind(registry, name, &wl_seat_interface, 1);
    }
}
static void on_remove(void *data, struct wl_registry *registry, uint32_t name) {
    (void)data; (void)registry; (void)name;
}
static const struct wl_registry_listener listener = { on_global, on_remove };

static uint32_t milliseconds(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t) != 0) return 0;
    return (uint32_t)((uint64_t)t.tv_sec * 1000 + t.tv_nsec / 1000000);
}
int main(void) {
    struct wl_display *display = wl_display_connect(NULL);
    if (!display) { fputs("Wayland compositor not accessible\n", stderr); return 1; }
    struct wl_registry *registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &listener, NULL);
    if (wl_display_roundtrip(display) < 0 || manager == NULL) {
        fputs("Compositor does not advertise wlroots virtual pointer\n", stderr);
        return 2;
    }
    struct zwlr_virtual_pointer_v1 *pointer =
        zwlr_virtual_pointer_manager_v1_create_virtual_pointer(manager, seat);
    if (!pointer || wl_display_roundtrip(display) < 0) {
        fputs("Could not establish persistent virtual pointer\n", stderr);
        return 2;
    }
    puts("READY");
    fflush(stdout);
    char line[128];
    while (fgets(line, sizeof(line), stdin)) {
        int x=0, y=0;
        if (sscanf(line, "move %d %d", &x, &y) == 2) {
            if (x < 0 || y < 0 || x > 1280 || y > 720) {
                fputs("Pointer coordinate out of range\n", stderr);
                return 2;
            }
            zwlr_virtual_pointer_v1_motion_absolute(pointer, milliseconds(),
                (uint32_t)x, (uint32_t)y, 1280, 720);
        } else if (strcmp(line, "down\n") == 0) {
            zwlr_virtual_pointer_v1_button(pointer, milliseconds(), BTN_LEFT,
                                           WL_POINTER_BUTTON_STATE_PRESSED);
        } else if (strcmp(line, "up\n") == 0) {
            zwlr_virtual_pointer_v1_button(pointer, milliseconds(), BTN_LEFT,
                                           WL_POINTER_BUTTON_STATE_RELEASED);
        } else if (strcmp(line, "quit\n") == 0) {
            break;
        } else {
            fputs("Unknown input injector command\n", stderr);
            return 2;
        }
        zwlr_virtual_pointer_v1_frame(pointer);
        if (wl_display_flush(display) < 0) {
            fputs("Virtual pointer connection lost\n", stderr);
            return 2;
        }
        puts("ACK");
        fflush(stdout);
    }
    zwlr_virtual_pointer_v1_destroy(pointer);
    zwlr_virtual_pointer_manager_v1_destroy(manager);
    if (seat) wl_seat_destroy(seat);
    wl_registry_destroy(registry);
    wl_display_disconnect(display);
    return 0;
}
