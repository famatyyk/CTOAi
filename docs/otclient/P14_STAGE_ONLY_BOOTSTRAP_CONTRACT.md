# P14 stage-only bootstrap contract

This contract prepares a newly built offline Windows guest before any P14
baseline, provisioning, snapshot, broker, visual capture, canary, rollback, or
release action. It is a file-copy boundary only. A successful result means
only that the exact manifest-listed files were copied into fixed local roots;
it is not runtime, visual, in-world, sandbox, rollback, or promotion evidence.

## Fixed roles and paths

The answer ISO places these source-controlled files in the guest:

~~~text
$OEM$\$$\Setup\Scripts\SetupComplete.cmd
$OEM$\$$\Setup\Scripts\ctoa_p14_post_oobe_bootstrap.ps1
$OEM$\$$\Setup\Scripts\ctoa_p14_guest_additions_setup.cmd
$OEM$\$$\Setup\Scripts\ctoa_p14_stage_bootstrap.ps1
~~~

SetupComplete.cmd runs once as LOCAL SYSTEM and installs only the fixed
post-OOBE Guest Additions task. It requires neither an operator password nor
interactive input. After that task verifies Guest Additions and completes its
controlled reboot, its second automatic logon clears the bootstrap credential,
disables autologon, and installs the fixed startup task
CTOAi-P14-Stage-Bootstrap for the *following* boot. The final `p14operator`
account has a blank password. The stage task also runs as LOCAL SYSTEM, so it
needs neither an operator password nor an interactive desktop. It reads only
this fixed VirtualBox shared-folder UNC path:

~~~text
\\VBOXSVR\CTOA_P14_STAGE
~~~

It copies only to these fixed guest roots:

~~~text
C:\P14Runner\repo
C:\P14Runner\client
C:\P14Runner\toolchain
~~~

The toolchain root makes the later guest provisioner independent of PATH:

~~~text
C:\P14Runner\toolchain\python\python.exe
C:\P14Runner\toolchain\git\cmd\git.exe
~~~

The bootstrap refuses an interactive or administrator identity; it must be
S-1-5-18 (LOCAL SYSTEM). It also refuses an active guest network adapter, any
reparse point, an existing nonempty C:\P14Runner, or an existing receipt.

## Transport layout and strict manifest

Before the host coordinator is run, its fixed host transport root must contain
exactly these three directories and nothing else:

~~~text
C:\P14Transport\ctoa-p14-stage\
  repo\
  client\
  toolchain\
~~~

repo is a clean full Git checkout with a real .git directory. It must not be a
linked worktree. client is the independently approved offline client payload.
toolchain contains the portable Python and Git locations above. Never place
profiles, logs, credentials, certificates, databases, .env files, runtime
state, or arbitrary host files in this root.

otclient_p14_stage_host.ps1 -Apply constructs the only accepted manifest at
the fixed path p14-stage-manifest.json; callers cannot pass a source path, VM
name, guest path, command, hash, or destination. The manifest is
ctoa.p14-stage-input.v1 with this exact shape:

~~~json
{
  "schema_version": "ctoa.p14-stage-input.v1",
  "source_revision": "<40 lowercase hex>",
  "file_count": 3,
  "files": [
    {
      "root": "repo",
      "path": "relative/forward-slash/path",
      "bytes": 1,
      "sha256": "<64 lowercase hex>"
    }
  ]
}
~~~

The guest accepts exactly the repo, client, and toolchain roots plus this
manifest at share top level. It rejects duplicate JSON keys, unknown keys,
unsafe or absolute paths, backslashes, traversal, control characters,
duplicates, case-colliding paths, empty required roots, reparse points,
special files, changed source files, and any extra or missing file. Every
source file is hashed and sized before the copy; source is hashed again and
the guest-local destination is hashed and sized after the copy. All three
checks must match the manifest.

No staged file is invoked by the bootstrap. In particular it does not launch
the client, Python, Git, capture, baseline, provisioner, broker, runner,
canary, or rollback code.

## Host coordinator and mandatory teardown

After the answer-ISO setup has installed the task and the fresh VM is powered
off, run the fixed coordinator:

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\zycie\CTOAi-p14-manifest-contract\scripts\windows\otclient_p14_stage_host.ps1 -Apply
~~~

The coordinator is fixed to CTOA-P14-Runner-Fresh-20260724. It fails closed
unless the VM is powered off, all NICs are disabled, clipboard, drag-and-drop,
VRDE, USB, and recording are disabled, and no shared folder is present. It
then:

1. creates the manifest in the fixed host transport root;
2. adds exactly CTOA_P14_STAGE as a read-only VirtualBox shared folder;
3. boots the VM headlessly and waits only for the fixed guest-property receipt
   hash;
4. requests an ACPI shutdown;
5. removes the share while the VM is powered off; and
6. independently verifies that no shared-folder mapping remains.

The coordinator never accepts a guest credential and never uses guestcontrol,
clipboard, drag-and-drop, VRDE, or keyboard/mouse injection. It does not take
a snapshot. If bootstrapping or teardown fails, do not reuse a partial guest
state. Restore/recreate the clean pre-stage guest and prepare a fresh host
transport root; the coordinator deliberately refuses to overwrite a manifest
or a partial destination.

The receipt is written only at:

~~~text
C:\ProgramData\CTOAi\P14\stage-bootstrap-receipt.json
~~~

Its authority fields keep staged_content_executed, baseline_created,
provisioned, runtime_actions, live_authority, and promotion_approved false.
The host sees only the receipt SHA-256 through /CTOAi/P14/StageBootstrap; it
never reads the guest filesystem through a second channel.

## Boundary after teardown

After the coordinator verifies share removal, the guest is still only staged.
The next separate operator action is the existing guest-local visual baseline
capture, followed by explicit owner approval and
otclient_p14_guest_provision.ps1 -Apply -ApproveVisualBaseline. Those actions
remain independently fail-closed and must not be inferred from the stage
receipt.
