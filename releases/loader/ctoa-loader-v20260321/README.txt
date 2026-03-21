CTOA Loader v20260321
=======================

Double-click the EXE to open the GUI app.
CLI mode is still available from Terminal.

Quick Start (GUI):
1. Double-click ctoa-loader-v20260321.exe.
2. Set source/target paths in the app window.
3. Use buttons: List / Sync / Open / Export.

Quick Start (Terminal / CLI):
1. Open terminal in this folder.
2. Verify checksum:
   certutil -hashfile ctoa-loader-v20260321.exe SHA256
3. List targets:
   .\\ctoa-loader-v20260321.exe list
4. Sync targets:
   .\\ctoa-loader-v20260321.exe sync --source <path> --target <path>

One-click mode:
- Double-click RUN-CTOA-LOADER.cmd and choose an option.
- Double-click RUN-CTOA-LOADER-SYNC-PL-BR.cmd for direct PL/BR sync presets.
- Edit ctoa-loader-paths.env.cmd once to set production paths 1:1.

Commands:
  list      - List available live targets
  sync      - Sync targets from source to target directory
  open      - Open target directory in file explorer
  export    - Export manifest of a specific target

For more info:
  .\\ctoa-loader-v20260321.exe --help
