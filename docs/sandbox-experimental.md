# Experimental Bubblewrap isolation (M8, incomplete)

The optional `--experimental-sandbox` argument wraps a **trusted** APK's ART
process using Bubblewrap's Linux user/mount/PID/network namespaces, *only*
with `--backend console`. The child receives a read-only `/usr` and runtime
library paths, a private `/tmp`, `/proc`, `/dev`, and read-only binds for
the framework DEX and APK at `/anx/`. Only a **single validated package's**
ART cache and app-data directories are mounted writable at `/anx/data`
and `/anx/apps/<package>`, respectively. Other ANX packages' data
directories are not mounted. The host home, `/etc`, other working directories, the
host `/run` and Wayland sockets are not mounted by the profile. The
Bubblewrap helper itself receives only a fixed `PATH` and `LANG` (rather than
the invoking shell's environment); `--clearenv` then supplies only the listed
guest variables to ART. ANX launches Bubblewrap with `close_fds=True` and
`stdin=/dev/null`, preventing host input streams and inherited nonstandard
file descriptors from reaching the child. **stdout/stderr remain connected to
the invoking terminal or redirection targets** for console diagnostics; they
are not a private logging boundary.

## Experimental child resource budgets

Only when `--experimental-sandbox` is selected, the single-threaded ANX
launcher applies Linux `setrlimit(2)` in the child **before** executing
Bubblewrap. Both soft and hard limits are tightened without ever increasing
a stricter pre-existing host limit:

| Kernel limit | ANX ceiling | Restriction |
| --- | --- | --- |
| `RLIMIT_CORE` | 0 bytes | Disables core dumps from the limited child |
| `RLIMIT_NOFILE` | 256 | Caps descriptors open by each descendant |
| `RLIMIT_FSIZE` | 256 MiB | Caps the size of a single file written |
| `RLIMIT_CPU` | 180 CPU seconds | Kernel CPU-time limit per process, **not elapsed time** |

A failure while applying any limit aborts the child *before* executing
Bubblewrap. No unsandboxed retry occurs. The limits are intentionally fixed
for this experimental profile and can reject otherwise valid large or
long-running apps. They do **not** cap aggregate disk usage, resident memory,
wall-clock time, the number of processes, network usage or I/O throughput.
`RLIMIT_NOFILE` also does not replace a file-descriptor capability policy.
A cgroup-based resource policy and hostile APK testing remain release blockers.

```sh
sudo apt install bubblewrap
bash scripts/build-demo-apk.sh
./anx run build/demo.apk --art /usr/bin/dalvikvm64 \
    --backend console --unsafe-host-execution --experimental-sandbox
```

This is **not a general permission framework, secure APK runtime or release
security certification**. All execution still requires explicit acknowledgement
of risk. There is no SELinux profile, seccomp filter, complete native dependency
policy, custom device mediation, hardened file descriptor policy, cross-process
permission model, or third-party penetration test.

The profile intentionally requires ART under `/usr` or `/bin`, rejects
Wayland mode, and never falls back to unrestricted execution if Bubblewrap is
absent or unprivileged namespace setup is forbidden.

Ubuntu 24.04's AppArmor rules can forbid unprivileged namespaces, in which
case Bubblewrap exits nonzero. **Do not disable host-wide namespace/AppArmor
restrictions to make this work**. The default console runtime still has no
sandbox; never run untrusted APKs.

## Verification and limitations

`python3 tests/sandbox-unit.py` checks bind policy and negative cases.
`bash tests/sandbox-smoke.sh` checks a fake Bubblewrap backend's received
arguments and proves that failed isolation never retries ART unsandboxed.
`python3 tests/sandbox-launcher-smoke.py` exercises the **real ANX CLI**
against a fake Bubblewrap helper while injecting a secret environment
variable, a host stdin file and a deliberately inheritable file descriptor.
It confirms all three are absent in the helper and checks the inherited
resource limits. `python3 tests/sandbox-limits.py` additionally verifies
resource ceilings, preservation of stricter inherited limits, unchanged
parent limits and fail-closed setup. The real `tests/sandbox-kernel.py`
probe checks those budgets inside the Bubblewrap guest on the privileged
CI runner. The helper test is not a kernel namespace isolation test.

**The unit and fake-helper tests are structural/mock tests, not evidence
that the kernel namespaces work on a target distro.** Successful runtime kernel isolation,
network denial, host-file denial, comprehensive quotas, Wayland permissions
and security audit are separate release gates.

## Real kernel isolation verification (development)

`python3 tests/sandbox-kernel.py` invokes an **actual Bubblewrap child**,
rather than a fake helper. On a Linux host permitting user namespaces it
checks that mount and network namespace identifiers differ from the host,
the host's home-only marker is inaccessible, inherited environment is
cleared, the APK and framework mounts are read-only, outbound TCP cannot
connect, and only explicitly writable ANX data directories persist writes, while
a sibling app package's data and ART runtime cache are inaccessible.

CI probes the unprivileged runner first. If Ubuntu's AppArmor/userns rules
reject namespace creation, the probe returns a distinct `UNSUPPORTED`
status (77), and the job records that the **normal-user profile is unusable
on this runner**; it does not disable AppArmor or retry ANX without isolation.
A separate **sudo/root CI-only probe** checks the actual kernel namespace
and filesystem policy with sufficient setup permissions. A root CI success
must not be represented as unprivileged Linux compatibility. Passing this probe would
support this specific profile on that CI runner, but **does not certify** a
complete sandbox (e.g. inherited stdout/stderr, seccomp, devices, TOCTOU, escapes,
third-party audits, and other distros are not covered).
