# P14 specialize static-copy fallback contract

This is the one-time fallback when the standalone `$OEM$` configuration-set
path does not deliver its files to a fresh guest. It uses the previously
bootable answer-medium flow, but does **not** depend on `$OEM$` mapping or on
`Microsoft-Windows-Setup/UseConfigurationSet`.

The fallback is only a fixed local-file transfer. It does not install Guest
Additions, register or run a task, stage any P14 payload, start a client,
connect to a network, restart Windows, or accept an operator credential. The
normal `SetupComplete.cmd` and post-OOBE LOCAL SYSTEM architecture remains
unchanged after the transfer succeeds.

## Required answer-medium layout

The answer ISO root contains the existing `Autounattend.xml` plus this exact
`P14Payload` directory. `copy.ps1` is a packaging name, not a new source file:

```text
P14Payload\copy.ps1
  <- scripts/windows/otclient_p14_specialize_static_copy.ps1
P14Payload\SetupComplete.cmd
  <- scripts/windows/otclient_p14_stage_setupcomplete.cmd
P14Payload\ctoa_p14_post_oobe_bootstrap.ps1
  <- scripts/windows/otclient_p14_post_oobe_bootstrap.ps1
P14Payload\ctoa_p14_guest_additions_setup.cmd
  <- scripts/windows/otclient_p14_guest_additions_setup.cmd
P14Payload\ctoa_p14_stage_bootstrap.ps1
  <- scripts/windows/otclient_p14_stage_bootstrap.ps1
```

Do not rely on a `$OEM$` directory for this fallback and do not set
`UseConfigurationSet` to `true` in this answer file. The medium is attached
after the Windows setup ISO and before the Guest Additions ISO; the bounded
scan permits only `D:` through `H:`. A different attachment topology is not
an approved substitution.

## Required specialize command

Add this `settings pass="specialize"` element to the existing
`Autounattend.xml`. It has no `Credentials` element. The first `Path` is 251
characters, below the 259-character Windows Setup limit.

```xml
<settings pass="specialize">
  <component name="Microsoft-Windows-Deployment" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
    <RunSynchronous>
      <RunSynchronousCommand wcm:action="add">
        <Description>CTOAi P14 static answer-media copy</Description>
        <Order>1</Order>
        <Path>"%SystemRoot%\System32\cmd.exe" /d /c for %D in (D E F G H) do @if exist "%D:\P14Payload\copy.ps1" "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%D:\P14Payload\copy.ps1"</Path>
        <WillReboot>Never</WillReboot>
      </RunSynchronousCommand>
      <RunSynchronousCommand wcm:action="add">
        <Description>CTOAi P14 static-copy success receipt check</Description>
        <Order>2</Order>
        <Path>"%SystemRoot%\System32\cmd.exe" /d /c if not exist "C:\ProgramData\CTOAi\P14\specialize-static-copy-receipt.json" exit /b 74</Path>
        <WillReboot>Never</WillReboot>
      </RunSynchronousCommand>
    </RunSynchronous>
  </component>
</settings>
```

`RunSynchronous` runs in the SYSTEM context during `specialize`. The copy
script repeats the `D:`--`H:` scan and requires exactly one
`P14Payload\copy.ps1` candidate; zero or multiple candidates fail closed.
It accepts only its own fixed media path, requires LOCAL SYSTEM, rejects
reparse points, and has no source, destination, network, or user-input
parameter.

## Copy and receipt behavior

The copy script creates only `C:\Windows\Setup\Scripts` as needed and copies
only the four files in the layout above. It hashes every medium source against
the source-controlled SHA-256 commitment, copies through a fixed temporary
file, verifies the temporary and final hashes, and copies `SetupComplete.cmd`
last. An existing destination with a different hash, any partial temporary,
or any changed/missing source is a terminal failure.

On complete success it creates this exact non-secret, create-new receipt:

```text
C:\ProgramData\CTOAi\P14\specialize-static-copy-receipt.json
```

The receipt records schema `ctoa.p14-specialize-static-copy.v1`, `copied`, the
bounded source root, the four filenames and their verified hashes. The second
command requires that success receipt. If the copy script begins and fails, it
writes instead:

```text
C:\ProgramData\CTOAi\P14\specialize-static-copy-blocked.json
```

Both receipt paths are create-new and mutually exclusive. A blocked, absent,
or ambiguous receipt cannot satisfy the success check; the fresh guest must be
rebuilt rather than retried over partial state.

## Boundary after specialize

The static copy itself is not P14 staging or runtime evidence. After setup
finishes, the copied `SetupComplete.cmd` performs its existing narrow action:
it installs the post-OOBE task as LOCAL SYSTEM. Only on the controlled next
startup can that task verify isolation and invoke the fixed Guest Additions
helper; only after its own reboot may it install the later stage bootstrap.
No visual, in-world, canary, rollback, or release claim follows from this
fallback.
