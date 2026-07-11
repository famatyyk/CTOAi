# Packet Index

## Status

Packet/protocol indexing is pending source.

The current workspace contains CTOAi and OTClient Lua modules, but not the TFS
fork or OTClient C++ protocol implementation needed to build an authoritative
packet index.

## What Is Known

- OTClient Lua modules use high-level client APIs (`g_game`, `g_map`,
  `LocalPlayer`, `Container`, `Map`, `Creature`) rather than raw packet parsing.
- CTOAi Python-side bot code primarily works through perception, input, template
  matching, generated Lua, and API/control surfaces.
- No opcode table, protocol version table, packet serializer, or server-side
  packet handler was found in the provided source snapshot.

## Required Source For Full Packet Index

Provide or locate:

- TFS fork source tree.
- `ProtocolGame` implementation.
- Client protocol parser/serializer sources.
- Opcode enum/header files.
- Lua script interface files.
- Custom packet handlers and extended opcodes.
- Login/game protocol version negotiation files.

## Future Index Format

Each packet entry should include:

- packet name
- opcode
- direction: client to server, server to client, or both
- source file and line
- payload fields and types
- validation rules
- event/hook triggered
- related Lua callback
- related CTOAi module
- tests or smoke path

## Rule

Do not add packet claims to prompts, docs, or code until backed by exact source
references.
