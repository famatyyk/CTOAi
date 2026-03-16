# ENC3 Reverse Engineering Runbook

**Last Updated:** 2026-03-15T00:00:00+01:00

## Overview
This runbook is the operational procedure for analyzing Mythibia's ENC3-protected runtime assets and determining whether a reliable unpacker or repacker is feasible.

Use this runbook after the safe loader paths are exhausted and plaintext `.otmod` injection is confirmed to fail with a decrypt fatal.

Current verified baseline:
- ENC3 files use a 24-byte wrapper.
- `U32@12` matches `file_length - 24` on sampled files.
- Payload entropy is high.
- No visible zlib header is present in the payload.
- No trivial single-byte XOR reveals a zlib stream.
- Public OTClient and OTCv8 upstreams do not expose a public ENC3 format for modules.

Primary local references:
- [scripts/ops/analyze-enc3.ps1](../scripts/ops/analyze-enc3.ps1)
- [scripts/ops/enc3-analysis-report.txt](../scripts/ops/enc3-analysis-report.txt)

## Goal
The objective is not to immediately build a packer. The objective is to prove the full decode path for one ENC3 file:

1. Locate the file-open and decrypt path in the executable.
2. Confirm the meaning of the ENC3 header fields.
3. Determine whether the payload is encrypted, compressed, or both.
4. Identify the key source or key-derivation path.
5. Recover one plaintext module or script from memory.
6. Decide whether writing an unpacker is realistic.

## Scope And Safety
This runbook is limited to:
- local static analysis of the Mythibia executable
- local dynamic debugging of the Mythibia process
- local extraction of already-owned runtime assets

Do not:
- test plaintext `.otmod` injection in `modules/`
- modify the production client binary
- patch instructions in the live process unless you are explicitly running a throwaway copy

Safe operating assumptions:
- keep the working client stable
- analyze a copied executable when possible
- preserve the current sync and rollback workflow

## Inputs
Required inputs:
- Mythibia executable under `%APPDATA%\Mythibia\MythibiaV2\`
- sample ENC3 files from `_tmp_unpack\`
- current analyzer output from [scripts/ops/enc3-analysis-report.txt](../scripts/ops/enc3-analysis-report.txt)

Recommended sample set:
- `_tmp_unpack\init.lua`
- `_tmp_unpack\modules\client\client.lua`
- `_tmp_unpack\modules\client\client.otmod`
- `_tmp_unpack\modules\game_trainer\trainer.lua`
- `_tmp_unpack\modules\game_trainer\trainer.otmod`

## Tools
Required tools:
- Ghidra
- x64dbg
- a hex viewer inside Ghidra or external

Optional tools:
- Detect It Easy or PE-bear for quick PE metadata inspection
- Process Hacker for module and handle visibility

## Output Artifacts
Store analysis outputs under `artifacts/enc3/` using a dated suffix.

Recommended artifact names:
- `artifacts/enc3/enc3-target-binary.txt`
- `artifacts/enc3/enc3-ghidra-string-xrefs.md`
- `artifacts/enc3/enc3-ghidra-header-model.md`
- `artifacts/enc3/enc3-x64dbg-breakpoints.md`
- `artifacts/enc3/enc3-memory-dump-notes.md`
- `artifacts/enc3/enc3-go-no-go.md`

If `artifacts/enc3/` does not exist, create it before starting the first session.

## Preflight Checklist
Before opening any reversing tool:

1. Confirm the stable client is not running.
2. Copy the target executable to a disposable analysis location.
3. Copy one or more ENC3 sample files into a scratch folder.
4. Record the exact binary filename and SHA256.
5. Record the exact sample filenames and sizes.
6. Keep [scripts/ops/enc3-analysis-report.txt](../scripts/ops/enc3-analysis-report.txt) open for side-by-side comparison.

Record the target binary in `artifacts/enc3/enc3-target-binary.txt` using this template:

```text
Binary path:
Binary filename:
Binary size:
Binary SHA256:
Analysis date:
Notes:
```

## Phase 1: Ghidra Static Triage
Expected outcome: identify the shortest path from file open to ENC3 verification and decrypt.

### Step 1. Create The Project
1. Open Ghidra.
2. Click `File` -> `New Project`.
3. Choose `Non-Shared Project`.
4. Name it `mythibia-enc3`.
5. Import the copied executable.
6. Accept default analysis settings for the first pass.
7. Wait for analysis to finish.

### Step 2. Locate High-Value Strings
1. Open `Search` -> `For Strings`.
2. Search for the following exact strings one by one:
   - `ENC3`
   - `unable to decrypt file`
   - `decrypt`
   - `encrypt`
   - `otmod`
   - `sandboxed`
   - `onLoad`
3. For each hit, open the listing and inspect cross references.

Save results in `artifacts/enc3/enc3-ghidra-string-xrefs.md`.

Use this table format:

| String | Address | XREF Function | Suspected Role | Confidence | Notes |
| --- | --- | --- | --- | --- | --- |
| ENC3 |  |  | magic check | high |  |
| unable to decrypt file |  |  | fatal/error path | high |  |

### Step 3. Find The Error Path First
Start from `unable to decrypt file` before chasing generic `decrypt` references.

1. Open the XREF for `unable to decrypt file`.
2. Identify the function that formats or logs the fatal.
3. Move one caller up if needed.
4. Determine what condition triggers the failure.
5. Note the arguments passed into the failing routine.

What to capture:
- function address
- decompiler name or temporary label
- whether the failure occurs before or after header parsing
- whether the failure occurs before or after payload transformation

### Step 4. Follow The File-Read Path
From the same call tree, identify the routine that reads the first bytes of the file.

Look for evidence of:
- comparison with `ENC3`
- fixed-length reads of 24 bytes
- reads of `U32` values from offsets near 4, 8, 12, 16, 20

If you find the header-read function, rename it in Ghidra to something explicit, for example:
- `enc3_read_header_candidate`
- `enc3_verify_magic_candidate`
- `enc3_decode_candidate`

### Step 5. Model The Header
As soon as the field reads are visible, record them in `artifacts/enc3/enc3-ghidra-header-model.md`.

Use this template:

```text
Header size candidate: 24 bytes

Offset 0:
  observed access:
  suspected meaning:

Offset 4:
  observed access:
  suspected meaning:

Offset 8:
  observed access:
  suspected meaning:

Offset 12:
  observed access:
  suspected meaning:

Offset 16:
  observed access:
  suspected meaning:

Offset 20:
  observed access:
  suspected meaning:
```

Expected minimum validation:
- verify whether offset 12 is used as payload length
- verify whether offset 16 is used as destination length or post-transform size
- determine whether offset 20 is flags, checksum, version, IV fragment, or unused

## Phase 2: Classify The Payload Transform
Expected outcome: determine the order and type of transformation.

### Step 6. Identify Compression Or Crypto Calls
In the candidate decode function, inspect:
- imports
- call graph
- constants
- loop structure

Look for these signatures:
- zlib or inflate-style calls
- XTEA delta `0x9E3779B9`
- AES-like tables or Windows crypto APIs
- simple XOR loops over a buffer
- checksum verification before or after transform

Record the transform pipeline in `artifacts/enc3/enc3-ghidra-header-model.md` under:

```text
Transform order candidate:
- header parse
- decrypt
- decompress
- checksum validate

Alternative candidate:
- header parse
- decompress
- decrypt
```

### Step 7. Identify Key Material Flow
Trace all inputs to the decode function and note whether key material comes from:
- hardcoded constants
- a separate helper function
- machine UUID or hardware fingerprint
- filename or path
- build version or revision
- runtime state or config

Mark the path using this table:

| Key Source Candidate | Where Found | Static Or Runtime | Confidence | Notes |
| --- | --- | --- | --- | --- |
| hardcoded buffer |  | static |  |  |
| machine identifier |  | runtime |  |  |
| filename-derived |  | runtime |  |  |

If the key source is unclear, stop broad browsing and move to dynamic confirmation.

## Phase 3: x64dbg Dynamic Confirmation
Expected outcome: catch the moment plaintext exists in memory.

### Step 8. Prepare The Debug Session
1. Launch x64dbg.
2. Open the copied Mythibia executable, not the production one.
3. Set the working directory to a copied client folder if possible.
4. Disable auto-restart behavior if present.

Record the session plan in `artifacts/enc3/enc3-x64dbg-breakpoints.md`.

### Step 9. Set Breakpoints In Priority Order
Set breakpoints in this order:

1. the function that logs `unable to decrypt file`
2. the candidate function that checks `ENC3`
3. the candidate function that decodes or decrypts payload
4. any candidate decompression call

If imported APIs are visible, add breakpoints on likely helpers only if they are directly in the call path.

For each breakpoint, record:
- address
- purpose
- caller expectation
- what memory buffer you expect to inspect

Template:

```text
BP1:
  address:
  purpose:
  expected registers:
  expected buffer:

BP2:
  address:
  purpose:
  expected registers:
  expected buffer:
```

### Step 10. Trigger A Known ENC3 Load
Use a known module load path. Prefer a startup-loaded module like `client.otmod` or `trainer.otmod`.

At each breakpoint capture:
- register state relevant to source and destination buffers
- input pointer
- input size
- output pointer
- output size
- any filename pointer or structure nearby

Write observations into `artifacts/enc3/enc3-memory-dump-notes.md`.

### Step 11. Validate Plaintext Emergence
The key dynamic question is whether plaintext appears in memory after the decode function returns.

You are looking for:
- OTML-like text beginning with `Module`
- Lua text beginning with normal source tokens like `function`, `local`, `g_`, `connect`, `modules.`
- decompressed but still encrypted-looking data

Decision rules:
- If readable text appears, dump that memory region immediately.
- If not, step into the next transform stage.
- If the buffer is still high entropy after the candidate decrypt function, the actual decrypt stage has not been reached yet.

## Phase 4: Minimal Success Criteria
Expected outcome: prove one file can be decoded end-to-end.

Minimum success means all of the following are true:

1. One ENC3 file is traced through the real decode path.
2. Header field meanings are confirmed from code, not only inferred from hex.
3. One plaintext OTML or Lua buffer is recovered from memory.
4. The transform order is known.
5. The key source is at least partially understood.

If all five are satisfied, you can design an unpacker.

If fewer than three are satisfied, do not write code yet.

## Phase 5: Go Or No-Go Decision
Write the outcome to `artifacts/enc3/enc3-go-no-go.md` using this template.

```text
Decision: GO / NO-GO / PARTIAL

What is confirmed:
-

What remains unknown:
-

Key source classification:
- static
- machine-bound
- runtime-bound
- unknown

Transform pipeline:
-

Can we build a minimal unpacker now?
- yes / no

Can we build a repacker now?
- yes / no

Reasoning:
-

Recommended next step:
-
```

Use these thresholds:

### GO
- plaintext recovered from memory
- transform order confirmed
- key source sufficiently known for a repeatable decode

### PARTIAL
- header fully modeled
- transform type known
- key source still unclear

### NO-GO
- no plaintext recovered
- key source appears session-bound or server-bound
- actual decode path remains ambiguous

## Common Pitfalls
- Chasing generic `decrypt` strings too early instead of starting from `unable to decrypt file`
- Assuming upstream OTClient crypto helpers are directly reused for ENC3 modules
- Confusing network crypto with file crypto
- Trying to infer the key before you have the real decode function
- Testing risky runtime injections before you understand the existing loader

## Observation Table
Use this during the session and paste it into the artifact notes.

| Phase | Tool | Target | Observation | Meaning | Next Action |
| --- | --- | --- | --- | --- | --- |
| strings | Ghidra | ENC3 |  |  |  |
| xref | Ghidra | unable to decrypt file |  |  |  |
| header | Ghidra | offset 12 read |  |  |  |
| decode | Ghidra | transform function |  |  |  |
| breakpoint | x64dbg | decode entry |  |  |  |
| memory | x64dbg | output buffer |  |  |  |

## End-Of-Session Exit Criteria
End the session only after one of these is true:

1. The decode path is mapped and plaintext is recovered.
2. The key source is proven to be impractical for local repacking.
3. The current binary copy is too protected or too noisy and a new approach is needed.

Before closing the session:
- save renamed functions in Ghidra
- export notes into `artifacts/enc3/`
- write the go or no-go decision
- record the single highest-value next breakpoint or function to inspect

## Recommended Immediate Execution Order
If you are starting now, do exactly this:

1. Create `artifacts/enc3/` and record the binary hash.
2. Open the copied executable in Ghidra.
3. Search `unable to decrypt file` and trace its caller.
4. Search `ENC3` and compare the nearby function set.
5. Rename the candidate header and decode functions.
6. Write the header model from code.
7. Open the same binary in x64dbg.
8. Set breakpoints on the error path, header check, and decode candidate.
9. Trigger one known module load.
10. Dump the first plaintext-looking buffer you see.
11. Write the go or no-go decision.

## References
- [scripts/ops/analyze-enc3.ps1](../scripts/ops/analyze-enc3.ps1)
- [scripts/ops/enc3-analysis-report.txt](../scripts/ops/enc3-analysis-report.txt)
- [docs/runbook-disk-emergency.md](runbook-disk-emergency.md)