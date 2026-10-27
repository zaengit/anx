# ANX development status

**Updated:** 2026-10-27. **Scope:** Linux x86_64, host ART, a deliberately
small Android framework subset. ANX is not a VM or general Android OS.

| Milestone | Status | Verification |
| --- | --- | --- |
| M0 — JVM proof of concept | Done | `tests/smoke.sh` on CI |
| M1 — Host ART bootstrap | Done on pinned reference | ART CI `HelloDex` + framework lifecycle |
| M2 — APK metadata/loader | Done for one-DEX/no-native subset | Binary manifest + independently SDK-compiled test APK |
| M3 — App and Activity lifecycle | Done for documented subset | `tests/framework-smoke.sh` and ART standalone APK |
| M4 — Wayland text/input backend | Experimental, headless integration verified | Native GTK4 + Weston + ART CI |
| M5 — Interactive APK v0.1 MVP | In progress: ART + Wayland verified headlessly | GTK click signal + live label update pass; **human pointer/desktop unverified** |
| M6 — Broader Android API coverage | Storage/preferences plus logging and own-package query subsets | JVM + ART tests; third-party APK matrix pending |
| M7 — Bionic/JNI/native ABI | Experimental host-x86_64 JNI pilot; Bionic and ABI translation not implemented | Native ELF/ZIP safety tests and host-ART JNI fixture |
| M8 — Sandbox, license, release | Experimental console Bubblewrap profile and consent gate; still unverified for hostile APKs | Fail-closed mock and policy tests; [Issue #6](https://github.com/zaengit/anx/issues/6) |

## Evidence

- [M3 merged PR #1](https://github.com/zaengit/anx/pull/1):
  [JVM/inspection CI](https://github.com/zaengit/anx/actions/runs/40356412073)
  and [ART CI](https://github.com/zaengit/anx/actions/runs/40356410618), both passed.
- [M4 experimental merged PR #7](https://github.com/zaengit/anx/pull/7):
  [native compile, Weston, JVM protocol CI](https://github.com/zaengit/anx/actions/runs/40358729768)
  and [ART subprocess bridge CI](https://github.com/zaengit/anx/actions/runs/40358729745), both passed.

## Blockers to call ANX ready

1. Test a truly standalone demo APK under **ART + native Wayland UI** on a
   graphical Linux desktop, click the Button and observe text change;
   verify resize/focus/close and lifecycle on the same run
   ([M4](https://github.com/zaengit/anx/issues/2),
   [M5](https://github.com/zaengit/anx/issues/3)).
2. Expand and verify the chosen compatible Android APIs with legal,
   redistributable third-party test APKs (M6).
3. Add architecture-matched JNI/native library loading with Bionic ABI
   compatibility (M7).
4. Sandbox untrusted APK processes, limit filesystem/network access,
   audit AOSP/native licenses, pin packaging dependencies and repeat
   security tests before a stable release (M8).

**Security warning:** ANX currently launches APK bytecode as a regular host
process. It does not sandbox it. Do not run untrusted APKs.

## Additional verified work

- [M5 ART + Wayland PR #8](https://github.com/zaengit/anx/pull/8):
  a real GTK4 Wayland window runs under headless Weston in the ART container,
  with a test-only GTK button signal and live label-update validation. It is
  not a physical pointer-input test.
- [M6 storage PR #9](https://github.com/zaengit/anx/pull/9):
  typed persistent preferences and per-package files with JVM/ART tests.
- M8 risk mitigation: CLI requires explicit acknowledgement for all unsandboxed
  execution. **This does not isolate the process or make third-party APKs safe.**

- [M5 live Handler PR #11](https://github.com/zaengit/anx/pull/11):
  `Handler.postDelayed()` now dispatches during an open Wayland window and
  a TextView is repainted without a click, verified on JVM and ART/Weston.

- Android SDK ABI fixture: the test APK source compiles against the official
  `android.jar`, not the ANX Java stubs. ART loads that APK independently,
  including its actual Android SharedPreferences return type descriptor and
  a GTK button interaction. This is **not** a broad third-party APK matrix.
