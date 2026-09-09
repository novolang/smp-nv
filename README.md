# smp-nv

**Status: NOT IMPLEMENTED — interface only.**

Every public function below is published with its signature and its
effect row, and every body is `todo()`.  Installing this package works;
calling it panics with `not implemented`.

## What this is

The Bluetooth Security Manager Protocol — Core Vol 3 Part H — as a state
machine that performs nothing.  Feed it PDUs, entropy and a person's
answer; it hands back the actions a host must take.  LE Legacy pairing
and LE Secure Connections, the cryptographic toolbox both are built out
of, and key distribution.

It has no radio, no clock, no random number generator and no flash.  It
has never heard of L2CAP beyond the number of the channel it rides on.

## Adding it, and checking it

```bash
novo pkg add smp-nv         # into your novo.toml
novo pkg build              # type- and effect-check the package
novo test tests/smp_tests.nv
```

`novo test` is red today and that is the point of the release: every
assertion below the first constant fails with `not implemented`.  The
tests are the pairing choreography written as executable text — each one
walks a step and checks that the action asked for is the one the
specification says comes next — so they turn green in the order an
implementation lane would want them to.

## The one example that will work

```novo
use smp

// One connection's pairing, driven to completion.  The host does
// everything; this package decides what.
fn pump(s: Smp, step: PairingStep) -> Smp
    var cur = step
    for i in 0..list.len(cur.actions)
        match cur.actions[i]
            Send(pdu)          => l2cap_send(smp.CID, pdu)
            NeedRandom(n)      => cur = smp.feed_random(cur.smp, entropy(n))
            Confirm(m, value)  => cur = smp.feed_user(cur.smp, ask(m, value))
            StartEncryption(k) => cur = smp.feed_link_encrypted(encrypt_link(cur.smp, k))
            StoreKeys(keys)    => save_bond(keys)
            Failed(reason)     => report(reason)
    cur.smp
```

Nothing in that loop knows how pairing works. That is the whole claim.

## The layer, and why

`core`, and the `Action` enum is what makes that true rather than
aspirational.

Pairing needs four things a `core` package may not have: entropy, a
person, a link that can be encrypted, and somewhere to write a bond.
Each is a variant this package RETURNS instead of an effect it declares.
`NeedRandom` is the sharpest one — a Security Manager that drew its own
nonces would need `[rand]`, and `[rand]` is `host`, and a `host`
package cannot go in firmware, which is the one place a peripheral's
pairing has to run.

`tests/embedded_probe.nv` is that claim in a form that either builds or
does not, and **it does not build** — for a reason that is about this
interface rather than about the toolchain, and is the most important
thing in this release.

Every function in `toolbox` takes and returns `[u8]`, and `[u8]` is a
heap list that `@tier(embedded)` forbids.  So there is no way to call
this package from a device without allocating, and no probe that both
exercises it and passes.  [crypto-nv](../crypto-nv) is the one published
`core` package that makes the device claim and keeps it, and how it does
so is the answer this package has not adopted: `pub @value struct Block`
with `w: [Int; 16]`, a true inline array laid out in the struct itself,
on the stack, with no header and no cell.  Every function in this
toolbox is fixed-width — 16 bytes for a block, 32 for a public-key
coordinate, 7 for an address, 3 for a prand — so the same treatment
applies throughout, and it would delete half the tests, because a width
could no longer be wrong.

That is a redesign of the interface and not a fix to a probe, which is
what `0.0.x` is for.  The probe stays red and names the reason.

A second, smaller finding sits behind it: the scratch package the audit
builds declares no dependencies, so a probe that reached `p256` could
not be compiled at all.  A `core` package with `core` dependencies
cannot make the full device claim the audit checks today.

## The load-bearing interface

```novo
pub enum Action
    Send(pdu: [u8])
    NeedRandom(bytes: Int)
    Confirm(method: Method, value: Int)
    StartEncryption(key: [u8])
    StoreKeys(keys: Keys)
    Failed(reason: Failure)
```

Six variants, and every effect a pairing needs is one of them.  Two
details in it are decisions rather than shapes.

**The actions are ordered, and the order is load bearing.**  A `Send`
before a `Failed` is the Pairing_Failed PDU the peer is owed; a host
that reordered them would take a device off the air before it had told
the peer why.

**`Failure` is both the error type and the wire format.**
`decode_pdu` returns `Result<Pdu, Failure>` where `Failure` is Table 3.7
— the codes a Pairing_Failed PDU carries.  A decode that failed has, by
construction, already worked out what to send back, and a caller that
had to map an error type onto those codes itself would be writing the
protocol twice.

## Where the crypto lives

Three packages, one rule: **a function goes where its specification
is.**

- [crypto-nv](../crypto-nv) has AES-128 and AES-CMAC — FIPS 197 and
  RFC 4493, useful to anyone.
- [p256-nv](../p256-nv) has the curve — FIPS 186-4, useful to TLS and
  JWT too.
- This package has `c1`, `s1`, `ah`, `f4`, `f5`, `f6`, `g2`, `h6` and
  `h7`, in `toolbox`.  Every one is Core Vol 3 Part H § 2.2, with
  Bluetooth's own key identifiers, salts, counters and byte orders in
  it, and no use outside Bluetooth pairing.

The dividing question is not "is it cryptography" — all of it is — but
"would a reader who has never opened the Core Specification have any use
for this function".

## The reference implementation, and what is NOT behind this interface

`orbit/ble`'s host stack: `src/host/smp.nv` (PDU shapes),
`smp_fsm.nv` (the state machine), `smp_ctx.nv`, `smp_compute.nv`,
`smp_handler.nv` and `smp_loop.nv`, plus `crypto-ble-ecc`'s
`smp_toolbox.nv` for the arithmetic.  The Core Spec's § D vectors are
the tests.

**Roughly half of this interface has nothing behind it**, and an
implementation lane should know which half before estimating:

| | in the reference |
| --- | --- |
| LE Legacy Just Works | yes — the FSM, the PDUs and c1/s1 all exist |
| LE Legacy Passkey Entry, OOB | no |
| LE Secure Connections | no state machine at all; `smp.nv` lists Pairing_Public_Key and Pairing_DHKey_Check as out of scope |
| f4, f5, f6, g2, h6, h7 | yes, with Core Spec vectors — and nothing calls them |
| Key distribution (§ 3.6) | no — opcodes 0x06 to 0x0A are out of scope, and `smp_fsm.nv` records that bond storage "is not implemented anywhere in this package" |
| Numeric Comparison, Keypress | no |
| Initiator role | no — the reference is peripheral-only |

The interface covers all of it because a Security Manager that offered
only Just Works would have to break its own API to grow, and because the
LE SC toolbox is already written and tested and merely unreachable.  But
the split is not a port: it is a port of the legacy half and a first
implementation of the rest.

**One more thing the reference could not do that this design assumes.**
Its state is not a value: `smp_ctx.nv` keeps the pairing context at a
fixed RAM address, `0x2000F820`, reached through `hw.mem_*`, so every
accessor carries `[hw]` and the whole SMP layer is `[hw]` by
transitivity — including the pure arithmetic.  It is also a singleton,
so the reference can pair with exactly one peer at a time.  `Smp` as a
value is what removes both, and it is the biggest single change between
the reference and this interface.

## Status

| item | implemented |
| --- | --- |
| `smp.CID` | yes — it is a constant |
| `smp.new`, `.begin`, `.feed`, `.feed_random`, `.feed_user`, `.feed_link_encrypted`, `.abort` | no |
| `smp.state`, `.method`, `.is_authenticated`, `.peer_public_key` | no |
| `smp.encode_pdu`, `.decode_pdu`, `.pdu_opcode` | no |
| `smp.Failure.message` | no |
| `toolbox.c1`, `.build_c1_p1`, `.build_c1_p2`, `.s1`, `.ah` | no |
| `toolbox.f4`, `.f5_mackey`, `.f5_ltk`, `.f6`, `.g2`, `.h6`, `.h7` | no |
