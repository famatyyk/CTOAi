# P14 Guest Additions setup contract

`scripts/windows/otclient_p14_guest_additions_setup.cmd` is the fixed,
one-time setup helper for a new P14 guest. It exists only to make VirtualBox
Guest Additions available before the stage-only bootstrap runs.

## Answer-ISO mapping

The answer ISO must copy the tracked helper to this exact target:

```text
$OEM$\$$\Setup\Scripts\ctoa_p14_guest_additions_setup.cmd
```

The clean-install answer file invokes that exact local path from `specialize`
with `RunSynchronous`, under LOCAL SYSTEM, with no arguments. The enclosing
`RunSynchronousCommand` owns the reboot policy; the helper never initiates a
reboot itself.

## Fixed behavior

The helper rejects arguments, a changed local path, and a caller that is not
LOCAL SYSTEM. It locates the mounted Guest Additions medium by the required
root-level `VBoxWindowsAdditions.exe`, then requires:

```text
cert\VBoxCertUtil.exe
cert\vbox*.cer
```

For every matching certificate it executes only the local, mounted-medium
command:

```text
VBoxCertUtil.exe add-trusted-publisher <certificate> --root <certificate>
```

Only after all certificate operations succeed does it execute the mounted
`VBoxWindowsAdditions.exe /S`. It accepts the normal installer completion
codes `0`, `3010`, and `1641`, and propagates other installer exit codes.

The helper has no parameters for credentials, hosts, paths, or any interactive
channel. It does not create a baseline, stage P14 content, provision an
appliance, or constitute visual/in-world/canary/rollback evidence.

## Exit contract

| Code | Meaning |
| --- | --- |
| 0, 3010, 1641 | Guest Additions installer completed or requested a restart. |
| 30 | Caller is not LOCAL SYSTEM. |
| 31 | Helper was not invoked from its fixed answer-ISO target path. |
| 32 | Helper received an argument. |
| 40 | No mounted Guest Additions installer was found. |
| 41 | Required certificate utility was missing. |
| 42 | No `vbox*.cer` certificate was present. |
| 43 | Certificate trust setup failed. |
| Other nonzero | Exit code from `VBoxWindowsAdditions.exe /S`. |
