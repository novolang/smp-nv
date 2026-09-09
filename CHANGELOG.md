# Changelog

Every published version, newest first. This file is on the publish
allow-list, so it travels with the package: it is the only thing a
consumer deciding whether to upgrade can read.

## 0.0.3 — 2026-09-10

- **Toolchain floor is 0.8.9**: the bodies and signatures use what 0.8.9 added (`todo()`, a bound effect parameter, the four layers), and the manifest says so instead of letting an older toolchain fail on an undefined function.  No signature changed.

## 0.0.2 — 2026-09-09

- **Dependencies are registry ranges**, not paths: the interface release 0.0.1 shipped a manifest whose dependencies pointed at sibling directories that exist only in the monorepo, so a consumer resolved the closure and then could not load the dependency.  No signature changed.

## 0.0.1 — 2026-09-09

The **interface**, before anyone implements it. Every signature, every
type and every effect row is published; every body is `todo()`, and the
release is stamped `NOT IMPLEMENTED — interface only`. Adding this
package works and calling it panics.

- `Smp` and `PairingStep`, and the seven functions that drive them: `new`,
  `begin`, `feed`, `feed_random`, `feed_user`, `feed_link_encrypted`
  and `abort`.
- `Action`, the enum every effect pairing needs comes back through, so
  the package declares none of them.
- `Role`, `IoCapability`, `Features`, `KeyDistribution`, `Method`,
  `Failure`, `Keys`, `UserResponse` and `State` — the vocabulary Core
  Vol 3 Part H negotiates in.
- `Pdu`, `encode_pdu`, `decode_pdu` and `pdu_opcode` — all fourteen SMP
  PDUs, for a capture tool or a conformance harness.
- `toolbox`: `c1`, `build_c1_p1`, `build_c1_p2`, `s1`, `ah`, `f4`,
  `f5_mackey`, `f5_ltk`, `f6`, `g2`, `h6` and `h7`.

Two things a reader should know before depending on it. Roughly half the
interface has no reference implementation behind it — LE Secure
Connections has no state machine in the stack this is split out of, and
key distribution is not implemented there at all; the README's table
says which half. And the reference keeps its pairing context at a fixed
RAM address rather than in a value, so it can pair with one peer at a
time; `Smp` as a value is the largest single change between the two.
