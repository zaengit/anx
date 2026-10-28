#!/usr/bin/env bash
# Try a truly delegated cgroup v2 kernel probe, never silently replace with a
# mocked success. All privileged setup is restricted to disposable systemd
# transient services; no controller changes to the runner's root cgroup.
set -euo pipefail

not_tested() {
  echo "::notice::Real cgroup v2 memory/pids enforcement NOT TESTED: $1"
}

if [[ ! -d /run/systemd/system ]] || ! command -v systemd-run >/dev/null; then
  not_tested "systemd system manager is unavailable on this runner"
  exit 0
fi
if ! command -v sudo >/dev/null || ! sudo -n true >/dev/null 2>&1; then
  not_tested "noninteractive sudo is unavailable for isolated CI-only setup"
  exit 0
fi

# First verify that systemd can create a delegated service. This command
# does not touch any user/system cgroup except a disposable test unit.
if ! sudo -n systemd-run --quiet --wait --collect --pipe \
     --property=Delegate=yes --property=MemoryAccounting=yes \
     --property=TasksAccounting=yes -- /usr/bin/true; then
  not_tested "systemd refused disposable delegated transient services"
  exit 0
fi

unit="anx-cgroup-probe-${BASHPID}-${RANDOM}.service"
set +e
sudo -n systemd-run --quiet --wait --collect --pipe \
  --unit="$unit" --property=Delegate=yes \
  --property=MemoryAccounting=yes --property=TasksAccounting=yes \
  -- /usr/bin/python3 "$PWD/tests/cgroup-systemd-ci.py"
status=$?
set -e

if [[ "$status" -eq 77 ]]; then
  not_tested "delegated controllers could not be activated in the transient service"
  exit 0
elif [[ "$status" -ne 0 ]]; then
  echo "::error::Real cgroup v2 kernel enforcement probe failed (exit $status)"
  exit "$status"
fi

echo "[PASS] Real kernel delegated cgroup v2 memory/pids enforcement and detached child teardown"
