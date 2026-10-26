# ANX development status

**Updated:** 2026-10-26. **Scope:** Linux x86_64, host ART, a deliberately
small Android framework subset. ANX is not a VM or general Android OS.

| Milestone | Status | Verification |
| --- | --- | --- |
| M0 — JVM proof of concept | Done | `tests/smoke.sh` on CI |
| M1 — Host ART bootstrap | Done on pinned reference | ART CI `HelloDex` + framework lifecycle |
| M2 — APK metadata/loader | Done for one-DEX/no-native subset | Binary manifest and APK inspection smoke |
| M3 — App and Activity lifecycle | Done for documented subset | `tests/framework-smoke.sh` and ART standalone APK |
| M4 — Wayland text/input backend | Experimental, not accepted end-to-end | GTK4 client under Weston headless; protocol test |
| M5 — Interactive APK v0.1 MVP | In progress, release gate open | ART + mock GUI click passes; *real visual desktop click unverified* |
| M6 — Broader Android API coverage | Not implemented | [Issue #4](https://github.com/zaengit/anx/issues/4) |
| M7 — Bionic/JNI/native ABI | Not implemented | [Issue #5](https://github.com/zaengit/anx/issues/5) |
| M8 — Sandbox, license, release | Not implemented | [Issue #6](https://github.com/zaengit/anx/issues/6) |

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
