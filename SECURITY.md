# Security policy (pre-release)

**ANX does not yet isolate APK code from the Linux host.** Android code runs as
a regular host process with the invoking user's privileges. It may access
files, credentials, network, devices, libraries, environment and processes
subject to those Linux user permissions. APK ZIP inspection, package-based
storage directories, classloading, and GTK subprocess boundaries are **not**
system security boundaries.

## Default execution policy

`anx inspect app.apk` parses metadata without executing app code.

`anx run app.apk` fails with exit code 2 before starting ART until
`--unsafe-host-execution` is supplied. This prevents accidental execution
but is **only an acknowledgement gate**, not isolation. Never use it for
untrusted binaries. A malicious APK can perform arbitrary actions on the host.

For tests using a known, trusted APK:

```bash
./anx inspect build/demo.apk
./anx run build/demo.apk --unsafe-host-execution --art /path/to/dalvikvm64
```

## Required before untrusted APK support (M8)

- A tested process sandbox restricting filesystem reads/writes, credentials,
  network, devices, IPC and subprocesses; least-privilege Wayland access.
- Resource limits, crash containment, package signature verification where
  relevant, and malware-resistant supply-chain/update procedures.
- Positive/negative security regression tests, threat model, platform
  compatibility and external review.
- Per-component dependency license and provenance audit before distribution.
- Explicitly documented native ABI, ART/libcore and Android API support matrix.

**Do not advertise ANX as secure for arbitrary third-party APKs.**

Report security concerns privately through the repository owner's security
contact/channel; do not include credentials or exploit artifacts in public
issue reports.

## Experimental console-only process isolation

`--experimental-sandbox --backend console --unsafe-host-execution` asks
Bubblewrap to create restricted Linux namespaces with a private mount view
and no host network. It refuses to run if the required helper/permissions
are missing. See [docs/sandbox-experimental.md](docs/sandbox-experimental.md).

This is a **development-only, unreviewed profile** and not grounds for
running untrusted APKs. The experimental child also inherits fixed Linux
`RLIMIT_CPU`, `RLIMIT_NOFILE`, `RLIMIT_FSIZE` and `RLIMIT_CORE` budgets
([details](docs/sandbox-experimental.md)); these are partial per-process
restrictions. An **additional opt-in** delegated cgroup v2 profile can cap
memory at 512 MiB and tasks (including threads) at 64, but requires an
already-delegated writable parent and has no unconfined fallback. The default
console sandbox does **not** enable this cgroup feature. Neither profile
controls wall time or total-disk usage. CI verifies
argument policy, fail-closed behavior and scoped kernel probes. It does
**not** certify resistance to hostile APKs or broad Linux compatibility.
