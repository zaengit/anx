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
long-running apps. These kernel rlimits do **not** cap aggregate disk usage,
resident memory, the number of processes, network usage or I/O throughput.
A separate parent-enforced wall-clock deadline is described below.
`RLIMIT_NOFILE` also does not replace a file-descriptor capability policy.
Full cgroup deployment compatibility and hostile APK testing remain release blockers.

## Wall-clock timeout for experimental sandbox

All `--experimental-sandbox` launches now have a **300-second elapsed-time
limit** by default, independent of the per-process `RLIMIT_CPU` budget.
Adjust it to between 1 and 3600 seconds using
`--sandbox-timeout-seconds 60` with `--experimental-sandbox`.
The timeout option is rejected without the experimental sandbox; invalid
values fail before launching Bubblewrap.

When the deadline expires, the launcher supervises Bubblewrap with
`subprocess.Popen`, forcibly kills and reaps the **direct Bubblewrap
process**, reports the timeout on stderr and exits with status `124`.
During an ordinary SIGTERM or SIGINT, the launcher also kills and reaps
the direct helper and unwinds its managed resources, returning `143`
(SIGTERM) or `130` (SIGINT). SIGTERM is converted into an exception only
while the sandbox cleanup scope is active; the prior signal handler is
restored afterward. There is never an unsandboxed retry. If the
optional delegated cgroup is active, leaving its context calls
`cgroup.kill`, checks that it is empty and removes it; this also covers
descendant processes. Without a delegated cgroup, Bubblewrap's
`--die-with-parent` offers only partial containment. A detached child
outside the Bubblewrap parent relationship is **not proven to be killed**
by the parent timeout or signal handler alone. Neither SIGKILL nor host
crashes allow Python cleanup handlers to run. This supervision is not an
independent kernel-enforced containment boundary or a security certification.

## Optional delegated cgroup v2 (experimental)

On Linux hosts with a **pre-existing writable, delegated cgroup v2 parent**
with `memory` and `pids` enabled in `cgroup.subtree_control`, ANX can
add a second, **explicitly requested** resource gate:

```sh
./anx run build/demo.apk --art /usr/bin/dalvikvm64 \
    --backend console --unsafe-host-execution --experimental-sandbox \
    --experimental-cgroup-parent "$CGROUP_PARENT"
```

The administrator/user must arrange an appropriate delegated child of
`/sys/fs/cgroup` in advance and set `CGROUP_PARENT` to its real path.
ANX never enables controllers, modifies the host's root cgroup, invokes
sudo, or weakens AppArmor. **No automatic cgroup fallback** is permitted.

Before launching Bubblewrap, ANX creates a fresh randomly named leaf under
that delegated parent and writes/verifies `memory.max=536870912` (512 MiB)
and `pids.max=64` (Linux tasks, including threads). Its pre-exec child
joins that leaf via `cgroup.procs`, after applying the existing rlimits;
failure aborts launch before untrusted bytecode can execute. On exit or
interruption ANX writes `1` to `cgroup.kill`, verifies
`cgroup.events: populated 0`, and removes only the ANX-created leaf.
If the kernel lacks `cgroup.kill`, delegation is missing, or any setup or
cleanup step fails, ANX reports an error instead of retrying without limits.

This is an **opt-in developer feature**, not a general host distribution
profile. The baseline experimental Bubblewrap mode without
`--experimental-cgroup-parent` does *not* gain RAM or aggregate task
budgets. Even with cgroup v2 enabled, the parent-managed timeout is not a
kernel wall-clock quota; there is still no disk capacity quota, I/O rate
limit, device mediation, seccomp policy,
hostile-APK safety certification, or multi-distribution verification.
Linux systems with a read-only/non-delegated cgroup hierarchy reject
the option as unsupported; do not disable security protections to run it.

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
parent limits and fail-closed setup. `python3 tests/cgroup-unit.py` checks
controller delegation, private leaf setup, join errors, forced failures and
cleanup using a **mock cgroup filesystem**; it does not prove real kernel
memory/process enforcement. `tests/sandbox-launcher-smoke.py` also checks
that the CLI rejects an unavailable cgroup rather than launching Bubblewrap.
On a machine with an **actually delegated** cgroup parent, run
`python3 tests/cgroup-kernel.py "$CGROUP_PARENT"` to validate real kernel
membership, configured budgets, the detached child's membership before
cleanup, and that it is no longer running after `cgroup.kill` and leaf
removal. **The same probe now actively checks both controllers:** it creates
a *separate* temporary ANX leaf with `pids.max=8` and verifies the kernel
rejects excess threads (including an increase in `pids.events max`); then it
creates another private leaf with `memory.max=64 MiB` and verifies that
a child allocating 128 MiB is killed by SIGKILL with an increase in
`memory.events oom_kill`. The reduced stress limits apply only inside
the probe's private disposable leaves, **not** the delegated parent, other
applications, or ANX's normal 512 MiB/64-task profile. This intentionally
provokes a contained OOM event and should only be used on a development
Linux host with sufficient headroom.

CI runs `python3 tests/cgroup-probe-unit.py` to ensure fake event counters,
missing thread denials, and absent OOM kills cannot generate false success.
The Linux CI kernel job also **attempts** an automatic *privileged,
CI-only* real probe using a disposable `systemd-run` transient service
with `Delegate=yes`. Inside that service, `tests/cgroup-systemd-ci.py`
verifies that it belongs to a fresh ANX-named service, moves its *own*
process into a manager leaf, enables `memory` and `pids` only in
that transient subtree, and invokes the real `tests/cgroup-kernel.py`
enforcement probe. It must never enable controllers in the host root or
other applications' groups. Failed controller enforcement is a **CI failure**;
unavailable systemd/delegation prints an explicit **NOT TESTED** notice, not
a false success. This test runs privileged and cannot establish
**unprivileged** distro compatibility. The tests intentionally create a
short-lived OOM *inside* the disposable private test cgroup.

Separately, for a runner with an existing *pre-delegated* parent, configure
the repository variable `ANX_CGROUP_TEST_PARENT` to its host path; the
sandbox-kernel job runs the same real stress probe as the current runner
and fails if controllers are not demonstrably enforced. Otherwise, that
manual integration prints **NOT TESTED**. Passing ordinary CI without an
explicit `[PASS] Real kernel delegated cgroup` output is **not** proof of
real cgroup enforcement on a target distro.
`python3 tests/sandbox-timeout-smoke.py` verifies that a hung fake
Bubblewrap process is killed after one second with status `124`, only
one launch occurs, invalid options are rejected and ordinary exit codes
remain unchanged. The same CLI test sends SIGTERM and SIGINT to an active
launcher and confirms statuses 143/130 and that the direct helper is
reaped without retry. The mocked cgroup unit test verifies teardown
after both timeout and SIGTERM, including restoration of the previous
signal handler. These are not real hostile-descendant tests.
The real `tests/sandbox-kernel.py`
probe checks kernel rlimits inside the Bubblewrap guest on the privileged
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
