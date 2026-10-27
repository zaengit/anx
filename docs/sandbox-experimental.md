# Experimental Bubblewrap isolation (M8, incomplete)

The optional `--experimental-sandbox` argument wraps a **trusted** APK's ART
process using Bubblewrap's Linux user/mount/PID/network namespaces, *only*
with `--backend console`. The child receives a read-only `/usr` and runtime
library paths, a private `/tmp`, `/proc`, `/dev`, and read-only binds for
the framework DEX and APK at `/anx/`. Only a **single validated package's**
ART cache and app-data directories are mounted writable at `/anx/data`
and `/anx/apps/<package>`, respectively. Other ANX packages' data
directories are not mounted. The host home, `/etc`, other working directories, the
host `/run` and Wayland sockets are not mounted by the profile. Inherited
environment variables are cleared before launching ART.

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

**The unit and fake-helper tests are structural/mock tests, not evidence
that the kernel namespaces work on a target distro.** Successful runtime kernel isolation,
network denial, host-file denial, resource limits, Wayland permissions and
security audit are separate release gates.

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
complete sandbox (e.g. seccomp, inherited FDs, devices, TOCTOU, escapes,
third-party audits, and other distros are not covered).
