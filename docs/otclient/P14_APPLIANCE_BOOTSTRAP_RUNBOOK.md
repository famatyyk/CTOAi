# P14 offline-appliance bootstrap runbook

This runbook creates the one-time offline P14 appliance baseline. It is an
operator procedure inside the dedicated guest; it does not authorize a live
client, network access, runtime actions, promotion, or an arbitrary
host-to-guest input channel. The later runner passes only a run ID and two
fixed cryptographic commitments through fixed VBox properties.

## Preconditions

- The approved source revision is checked out cleanly at
  `C:\P14Runner\repo` in the dedicated standard guest account.
- The known OTClient build, its DAT/SPR pair, and the tracked Helper package
  are already present at their fixed guest paths.
- Portable Python and Git must be present at their fixed staged toolchain
  paths; the guest provisioner does not use PATH discovery.
- VirtualBox Guest Additions and the guest desktop are available. Before the
  guest is booted for the capture, disable every VM NIC and integration
  channel: shared folders, shared clipboard, drag and drop, VRDE, USB
  passthrough, and VM recording.
- Work only at the guest console. Do not use RDP, VRDE, guest-control,
  workstation keyboard/mouse injection, or a shared clipboard to perform this
  procedure.

The capture and provisioning scripts independently reject a non-interactive
session, an administrator account, a non-clean checkout, an enabled guest
network adapter, a reparse-point evidence path, or a missing guest identity.

## 0. Required stage-only bootstrap for a new guest

Before a newly built guest reaches this runbook, use the LOCAL SYSTEM,
manifest-bound stage bootstrap and its host coordinator from
[P14_STAGE_ONLY_BOOTSTRAP_CONTRACT.md](P14_STAGE_ONLY_BOOTSTRAP_CONTRACT.md).
It is the only allowed one-time transfer path and it verifies shared-folder
teardown before any capture or provision operation.

<!-- Legacy manual-copy wording retained only for historical context. It is
superseded and must not be used. If the reviewed bundle must first be copied into the guest, a transient
read-only shared folder is allowed only for that transfer while the appliance
is still being assembled. Copy the reviewed source into
`C:\P14Runner\repo`, verify the checkout is clean, then remove the shared
folder completely. It must not exist during baseline capture, provisioning, or
snapshot creation; the host runner rejects any shared folder, including a
read-only one.
-->

## 1. Capture a candidate baseline in the guest

In the already logged-in, offline guest console, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\P14Runner\repo\scripts\windows\otclient_p14_baseline_capture.ps1 -Apply
```

The script launches only the fixed guest-local client capture, records the
in-world Helper marker, and writes these fixed local artifacts:

- `C:\P14Runner\baseline\p14-baseline-<source-revision>.png`
- `C:\P14Runner\baseline\baseline-capture-report.json`
- `C:\P14Runner\baseline\baseline-client-capabilities.json`
- `C:\P14Runner\baseline\baseline-receipt.json`

It refuses a nonempty baseline directory. A partial or failed attempt must be
rebuilt from a clean guest snapshot; do not hand-edit, replace, or copy a
baseline receipt or image.

## 2. Owner review and explicit approval

The owner reviews the guest-local PNG at the fixed baseline path while still at
the guest console. The image must show the expected client window and the
expected in-world Helper state. Keep the image, receipt, and associated files
inside the guest; they are not a workstation screenshot or an upload artifact.

After that review, the owner expresses approval only by supplying the explicit
`-ApproveVisualBaseline` switch to the provisioner. There is deliberately no
hand-typed image hash: the provisioner recalculates every hash from the fixed
receipt, image, capture report, and runtime marker before it creates the
snapshot manifest.

## 3. Provision the immutable guest appliance

Use the logical snapshot ID for the fixed offline appliance. For the current
appliance, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\P14Runner\repo\scripts\windows\otclient_p14_guest_provision.ps1 -Apply -SnapshotId p14-offline-20260724 -ApproveVisualBaseline
```

The provisioner fails closed unless the receipt is a candidate generated for
the exact clean guest revision, all hashes and image dimensions match, the
capture and Helper report prove guest isolation, and the owner approval switch
is present. It stages the tracked package, creates or validates the
non-exportable guest evidence certificate, writes the snapshot manifest, then
makes the repo, package, trust, and baseline trees read-only. It also publishes
the immutable raw snapshot manifest (base64) and its exact raw SHA-256 through
two fixed, non-secret VBox guest properties. They are consumed once by the
host-side binder; no shared folder, clipboard, typed hash, credential, or
guest-control channel is used.

Record no private key, raw receipt, image, or certificate-store contents.

## 4. Create and bind the resumable offline VM snapshot

After provisioning, sign out and sign back in once to start the fixed HKCU
broker. Leave that dedicated standard-user desktop session open. Recheck that
every NIC and integration channel remains disabled, but leave the VM running
and do not take a snapshot yourself. The binder performs the only savestate and
snapshot operation after it has consumed and erased the one-time manifest
export. The resulting saved state is deliberate: VirtualBox resumes it exactly,
so the fixed broker can receive a later bounded run ID without any password,
guest-control command, autologon, RDP, or synthetic input.

Then, on the host, run the fixed-path binder from the clean B0 checkout:

```powershell
$P14HostCheckout = 'C:\Users\zycie\CTOAi-p14-uuid-binding'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $P14HostCheckout 'scripts\windows\otclient_p14_appliance_bind.ps1') -Apply
```

The binder derives the offline VM UUID, logical snapshot ID, and final snapshot
UUID itself, pins them in `C:\ProgramData\CTOAi\P14\p14-appliance-binding.json`,
makes that record read-only, and prints its raw SHA-256. It never accepts a VM
UUID, snapshot UUID, snapshot name, binding path, or hash argument. It also
clears the one-time manifest export properties. Never substitute a mutable
snapshot name for the UUID. The prior NAT-capable snapshot is not an acceptable
fallback.

## 5. Pin the public B1 commitments

Set only these public values in the protected `p14-independent-runner`
environment after the binder succeeds: the guest public certificate, key ID,
logical snapshot ID, guest source revision, snapshot-manifest SHA-256, and
appliance-binding SHA-256. The last two values are emitted by the provisioner
and binder; do not hand-enter or derive them from a screenshot. The protected
workflow verifies them against the guest-signed receipt before it accepts any
visual, in-world, canary, or rollback result.

Only after the immutable snapshot and its source binding are in place may the
host runner perform an isolated run. The runner remains limited to visual and
in-world capture plus sandbox-only canary/rollback evidence; it does not grant
live-network, runtime-action, or promotion authority.
