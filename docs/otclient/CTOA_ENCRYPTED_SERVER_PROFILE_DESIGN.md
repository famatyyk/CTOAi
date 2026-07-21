# CTOA Encrypted Server Profile Design

## Purpose

Provide one simple connection UI for OTClient, OTCv8, OTC Brasil, and derived
forks without pretending their login, protocol, RSA, updater, or HTTP surfaces
are identical.

## Product Shape

The visible profile contains server name, host, game/login ports, client and
protocol version, selected fork adapter, optional website/update endpoints,
certificate or public-key pin status, and a clear Connect button. Advanced
adapter fields stay collapsed unless the selected fork proves they are needed.
The public portable portion validates against
`schemas/otclient-server-profile.schema.json`. It stores a `credential_ref`,
never a password, account secret, token, private key, or reusable session.

## Security Boundary

- Persist an authenticated encrypted envelope, not plaintext credentials.
- Generate a random data-encryption key per profile and wrap it with a key held
  by Windows Credential Manager/DPAPI (or the native OS keystore on other hosts).
- Prefer an AEAD construction such as AES-256-GCM or XChaCha20-Poly1305 with a
  versioned envelope, random nonce, and profile metadata as associated data.
- Never invent transport encryption. Use TLS and certificate/public-key pinning
  where the server and fork support them; otherwise show the transport as
  unverified instead of calling it encrypted.
- Never write passwords, session tokens, private keys, decrypted envelopes, or
  full account identifiers to logs, crash reports, Engine Brain, or evidence.
- Decryption exists only in memory for the explicit connect operation and the
  buffer is released immediately after adapter handoff.
- Bind each short-lived session handle to the selected profile, endpoint,
  adapter, process id, nonce and expiry. Logout, process exit, timeout or a
  profile switch destroys it.

## Adapter Contract

Every fork adapter reports capabilities before activation: login flow, protocol
range, RSA/public-key model, TLS support, endpoint model, updater requirements,
credential fields, and whether identity pinning is possible. Unsupported or
ambiguous capabilities fail closed. The normalized UI produces a data-only
connection intent; the adapter validates and translates it into fork-native
calls. Safe and Helper automation state are not inputs to this process.

The first named adapters are `otclient-edubart`, `otcv8`, `otcbr`, and
`redemption-mehah`. Derived clients declare a base adapter and bounded
capability overrides rather than duplicating the entire connector.

## Delivery Order

1. Passive fork and capability detection with a redacted diagnostic report.
2. Versioned profile schema, validation, migration, and encrypted import/export.
3. UI prototype with no connect dispatch and explicit transport trust status.
4. One adapter at a time under fixture and sandbox validation.
5. Explicit-connect acceptance, negative tests, audit redaction, and rollback.

No generic adapter is allowed to silently downgrade TLS, skip a required pin,
or guess protocol/RSA settings to make a connection appear successful.

### Implemented foundation

`scripts/ops/otclient_fork_capability_detector.py` implements delivery step 1
as a bounded, read-only detector. It inspects only fixed public marker files and
capability paths, never `.env`, settings, profiles or credentials, and never
connects. It identifies the current `C:\otclient` source as
`redemption-mehah` with both Redemption/mehah primary markers and reports the
proven UIItem, action-bar, keybind, shader and HTML capabilities. The protected
live Solteria package intentionally reports `unknown` because its module/source
markers are not available as loose files; this is a fail-closed result, not an
adapter guess.
