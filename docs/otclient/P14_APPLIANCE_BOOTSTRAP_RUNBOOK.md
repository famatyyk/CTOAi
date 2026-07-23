# P14 offline-appliance bootstrap runbook

This runbook creates the one-time offline P14 appliance baseline. It is an
operator procedure inside the dedicated guest; it does not authorize a live
client, network access, runtime actions, promotion, or a host-to-guest input
channel.

## Preconditions

- The approved source revision is checked out cleanly at
  `C:\P14Runner\repo` in the dedicated standard guest account.
- The known OTClient build, its DAT/SPR pair, and the tracked Helper package
  are already present at their fixed guest paths.
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

## 0. Optional one-time source transfer

If the reviewed bundle must first be copied into the guest, a transient
read-only shared folder is allowed only for that transfer while the appliance
is still being assembled. Copy the reviewed source into
`C:\P14Runner\repo`, verify the checkout is clean, then remove the shared
folder completely. It must not exist during baseline capture, provisioning, or
snapshot creation; the host runner rejects any shared folder, including a
read-only one.

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

Use the logical snapshot ID that matches the source-controlled host runner
binding. For the current appliance name, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\P14Runner\repo\scripts\windows\otclient_p14_guest_provision.ps1 -Apply -SnapshotId p14-offline-20260724 -ApproveVisualBaseline
```

The provisioner fails closed unless the receipt is a candidate generated for
the exact clean guest revision, all hashes and image dimensions match, the
capture and Helper report prove guest isolation, and the owner approval switch
is present. It stages the tracked package, creates or validates the
non-exportable guest evidence certificate, writes the snapshot manifest, then
makes the repo, package, trust, and baseline trees read-only.

Record only the emitted guest evidence public certificate, key ID, and logical
snapshot ID in the approved GitHub environment variables. Do not export the
private key, raw receipt, image, or certificate-store contents.

## 4. Create and bind the offline VM snapshot

Power the guest off. Recheck that every NIC and integration channel remains
disabled, set the fixed endpoint profile, and create the named snapshot for the
prepared appliance. Record its generated UUID exactly. The follow-up appliance
binding must pin that UUID before the host runner may start the VM; never
substitute a mutable snapshot name for the UUID. The prior NAT-capable snapshot
is not an acceptable fallback.

Only after the immutable snapshot and its source binding are in place may the
host runner perform an isolated run. The runner remains limited to visual and
in-world capture plus sandbox-only canary/rollback evidence; it does not grant
live-network, runtime-action, or promotion authority.
