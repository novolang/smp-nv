# Changelog

Every published version, newest first. This file is on the publish
allow-list, so it travels with the package: it is the only thing a
consumer deciding whether to upgrade can read.

## 0.0.5 — 2026-09-25

The package builds with novo 0.11.  Every body is still `todo()`.

- The lock file moves crypto-nv 0.1.1 to 0.1.6.  crypto-nv 0.1.1 writes
  into lists through names that are not declared `var`, which novo 0.11
  refuses (E2038), so this package did not build with novo 0.11 against
  it.  No requirement in the manifest changed.

## 0.0.4 — 2026-09-15

README rewritten to the package README style guide (docs/writing-a-readme.md); no change to the interface.

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

### Design notes

Moved here from the README, which now states only what a user needs.

- Roughly half of this interface has nothing behind it in the stack it
  is split out of, and an implementation lane should know which half
  before estimating. `orbit/ble`'s host stack is `src/host/smp.nv`
  (PDU shapes), `smp_fsm.nv` (the state machine), `smp_ctx.nv`,
  `smp_compute.nv`, `smp_handler.nv` and `smp_loop.nv`, plus
  `crypto-ble-ecc`'s `smp_toolbox.nv` for the arithmetic.

  | | in the reference |
  | --- | --- |
  | LE Legacy Just Works | yes — the FSM, the PDUs and c1/s1 all exist |
  | LE Legacy Passkey Entry, OOB | no |
  | LE Secure Connections | no state machine at all; `smp.nv` lists Pairing_Public_Key and Pairing_DHKey_Check as out of scope |
  | f4, f5, f6, g2, h6, h7 | yes, with Core Spec vectors — and nothing calls them |
  | Key distribution (§ 3.6) | no — opcodes 0x06 to 0x0A are out of scope, and `smp_fsm.nv` records that bond storage "is not implemented anywhere in this package" |
  | Numeric Comparison, Keypress | no |
  | Initiator role | no — the reference is peripheral-only |

  The interface covers all of it because a Security Manager that
  offered only Just Works would have to break its own API to grow, and
  because the LE SC toolbox is already written and tested and merely
  unreachable. The split is therefore a port of the legacy half and a
  first implementation of the rest.
- The reference's state is not a value. `smp_ctx.nv` keeps the pairing
  context at a fixed RAM address, `0x2000F820`, reached through
  `hw.mem_*`, so every accessor carries `[hw]` and the whole SMP layer
  is `[hw]` by transitivity, the pure arithmetic included. It is also a
  singleton, so the reference can pair with exactly one peer at a time.
  `Smp` as a value removes both, and it is the biggest single change
  between the reference and this interface.
- A second finding sits behind the embedded probe's failure: the
  scratch package the shard audit builds declares no dependencies, so a
  probe that reached `p256` could not be compiled at all. A `core`
  package with `core` dependencies cannot make the full device claim
  the audit checks today.
