# smp-nv

The Security Manager Protocol (SMP) is how two Bluetooth Low Energy
devices agree on the keys that encrypt a link. It is specified in the
[Bluetooth Core Specification](https://www.bluetooth.com/specifications/specs/core-specification/),
Volume 3, Part H. This package brings it to novo-lang as a state machine
that performs nothing: feed it packets, entropy and a person's answer,
and it hands back the actions a host must take. It runs on a channel
that [l2cap-nv](https://novo-lang.org/packages/l2cap-nv) provides.
[att-nv](https://novo-lang.org/packages/att-nv) is its sibling on the
next channel along, and it is what most of the encryption this package
arranges is for.

**Status: NOT IMPLEMENTED — interface only.** Every function is declared
with its full signature, but every body is a `todo()` that panics when
called. The package is published so its design can be reviewed and
depended on before it is implemented. Version 0.1.0 will be the first
working release.

## What the Security Manager is

**Pairing** is the procedure that gives two devices a shared key.
**Bonding** is pairing plus storing that key, so the next connection
skips the procedure. SMP is the protocol both run over, on L2CAP channel
0x0006.

There are two families. **LE Legacy pairing** is the original: the two
sides exchange a confirm value and a nonce, derive a short-term key from
them, and use it to encrypt the link long enough to distribute the real
keys. **LE Secure Connections** replaced it in Bluetooth 4.2: the two
sides exchange public keys on the P-256 curve, run Elliptic Curve
Diffie-Hellman, and derive the long-term key from the shared secret. The
SC bit of the AuthReq field in the first packet chooses between them.

Within a family, the **pairing method** is decided by what each device
can show and what it can be told, which the specification calls its
**IO capability**. Section 2.3.5.1 gives the table. The method decides
whether the pairing has **man-in-the-middle protection**, which is the
guarantee that the device you paired with is the one you meant.

| Method | What the person does | Man-in-the-middle protection |
| --- | --- | --- |
| Just Works | Nothing | None |
| Passkey Entry | Reads six digits on one device and types them into the other | Yes |
| Numeric Comparison | Compares six digits shown on both and confirms | Yes, and only under Secure Connections |
| Out of Band | Nothing on this link. The data arrives by another channel | As good as that channel |

When pairing succeeds the two sides distribute whatever keys they
negotiated (section 3.6): the **long-term key** (LTK) that encrypts
future connections, the **identity resolving key** (IRK) that lets a
peer recognise a device using a rotating random address, and the
**connection signature resolving key** (CSRK) that signs writes on an
unencrypted link.

| Quantity | Value |
| --- | --- |
| The channel SMP runs on | CID 0x0006 |
| An encryption key size | 7 to 16 octets |
| A confirm value, a nonce and a key | 16 bytes |
| A public-key coordinate | 32 bytes |
| An address in the toolbox | 7 bytes: the type byte, then six address bytes |
| The prand of a resolvable address | 3 bytes |
| A passkey and a comparison value | Six decimal digits, 0 to 999999 |

Underneath both families is what the specification calls the
**cryptographic toolbox**, section 2.2: nine functions built out of
AES-128 and AES-CMAC with Bluetooth's own key identifiers, salts,
counters and byte orders in them.

| Function | Section | What it computes |
| --- | --- | --- |
| `c1` | 2.2.3 | The LE Legacy confirm value |
| `s1` | 2.2.4 | The LE Legacy short-term key |
| `ah` | 2.2.2 | The hash that resolves a resolvable private address |
| `f4` | 2.2.6 | The Secure Connections confirm value |
| `f5_mackey`, `f5_ltk` | 2.2.7 | The MacKey and the long-term key, from the Diffie-Hellman secret |
| `f6` | 2.2.8 | The check value each side sends to prove it derived the same key |
| `g2` | 2.2.9 | The six digits a person compares |
| `h6` | 2.2.10 | The link-key conversion for cross-transport derivation |
| `h7` | 2.2.11 | The salted conversion the CT2 bit selects instead of `h6` |

This package performs no input or output. It has no radio, no clock, no
random number generator and nowhere to write a bond. Pairing needs all
four, and each one comes back as an **action** the host performs and
reports on. That is what lets a Security Manager be a package rather
than a layer of a stack, and what lets the same code run in a phone's
host and in a peripheral's firmware.

| Action | What the host does |
| --- | --- |
| `Send` | Puts the bytes on L2CAP CID 0x0006 |
| `NeedRandom` | Draws that many bytes of entropy and calls `feed_random` |
| `Confirm` | Asks the person and calls `feed_user` |
| `StartEncryption` | Starts link-layer encryption with the key, then calls `feed_link_encrypted` |
| `StoreKeys` | Writes the bond against the peer's identity, or drops it |
| `Failed` | Reports that pairing is over and will not resume |

## Install

```
novo pkg add smp-nv
```

## Example

```novo
use smp

fn main() [io]
    // What this device asks for and will accept. The key size is in
    // octets and the two sides take the smaller of the two.
    let features = Features {
        bonding: true, mitm: true, secure_connections: true,
        keypress: false, ct2: false, oob: false,
        max_key_size: 16,
        initiator_keys: KeyDistribution { enc: false, id: true, sign: false, link: false },
        responder_keys: KeyDistribution { enc: true, id: true, sign: false, link: false } }

    // A peripheral that can show six digits and be told yes or no.
    let s = smp.new(Responder, features, DisplayYesNo)

    // Starting asks the central to pair. Everything the host must do
    // comes back as an action, in the order it must happen.
    let step = smp.begin(s)
    for i in 0..list.len(step.actions)
        match step.actions[i]
            Send(pdu)          => println("put ${list.len(pdu)} bytes on CID ${smp.CID}")
            NeedRandom(n)      => println("draw ${n} bytes of entropy")
            Confirm(_, value)  => println("ask the person about ${value}")
            StartEncryption(k) => println("encrypt the link with a ${list.len(k)}-byte key")
            StoreKeys(_)       => println("write the bond to flash")
            Failed(reason)     => println("pairing stopped: ${reason.message()}")
```

A real host does the same loop with real work in each arm, and feeds the
answer back with `feed_random`, `feed_user` or `feed_link_encrypted`.
Nothing in the loop knows how pairing works.

Build and test with `novo pkg build` and `novo test`. Today `novo test`
fails on purpose: every test reaches a `not implemented: smp.<fn>`
panic. The tests are the specification the implementation will have to
satisfy.

## What the package contains

| Module | Contents |
| --- | --- |
| `smp` | The protocol. The state machine and the seven functions that drive it, the actions it returns, the vocabulary the two sides negotiate in, and all fourteen SMP packets with their encoder and decoder. |
| `toolbox` | The nine cryptographic functions of section 2.2, as total functions over fixed-width byte strings. |

## How to choose an entry point

**The state machine is the ordinary way in.** `new` builds one, `begin`
starts a procedure, and `feed`, `feed_random`, `feed_user` and
`feed_link_encrypted` advance it. Each returns the new state machine and
the actions to perform. `state`, `method` and `is_authenticated` report
on it without driving it.

**`encode_pdu` and `decode_pdu` are the codec underneath.** A host
driving the state machine never needs them, because it passes bytes. A
packet-capture tool, a test and a conformance harness all do.

**The toolbox is for whoever is checking the arithmetic.** Its nine
functions are what the state machine is made of. Call them directly to
run the Core Specification's own vectors, or to compute one value
outside a pairing, such as resolving a private address with `ah`.

## The rules a user needs

1. **Feed exactly the entropy that was asked for.** `NeedRandom` names a
   byte count, and the source must be one you trust. Feeding fewer
   bytes, or feeding when none was asked for, gives
   `Failed(UnspecifiedReason)`. A pairing that continued on short
   entropy would be worse than one that stopped.
2. **The actions are in the order they must happen.** A `Send` before a
   `Failed` is the Pairing_Failed packet the peer is owed. A host that
   reordered them would take a device off the air before telling the
   peer why.
3. **`feed` never refuses.** A packet that does not decode, or that is
   not legal in the current state, produces a `Send` of Pairing_Failed
   and then a `Failed`. The peer is owed an answer, and a caller that
   had to build that packet itself would be writing the protocol twice.
4. **Say when the link is encrypted.** `feed_link_encrypted` is what
   moves a legacy procedure past the short-term key and lets key
   distribution begin. A host that starts encryption and forgets to
   report it leaves the peer waiting for keys that never come.
5. **`method` is `None` until both sides have spoken.** The method
   depends on what the peer said, and guessing early is how a stack ends
   up displaying a passkey for a Just Works pairing (Core Vol 3 Part H
   section 2.3.5.1).
6. **`is_authenticated` is false for Just Works.** It stays false
   however many sides asked for man-in-the-middle protection, because
   asking is not getting. Check it before treating the link as trusted.
7. **Every field of `Keys` is optional.** What arrives is what the two
   sides negotiated. A Secure Connections bond distributes no long-term
   key at all, because both sides derived the same one from `f5`, and
   the EDIV and Rand pair is legacy's way of naming a stored key
   (section 3.6).
8. **The encryption key size is negotiated down.** It is 7 to 16 octets
   and the two sides take the smaller. A peer that asks for less than
   this device's own minimum is refused with `EncryptionKeySize`
   (section 3.5.1).
9. **A packet fed in is the L2CAP payload.** The opcode byte comes
   first and the four-byte L2CAP header is already off (section 3.1).
10. **`Failure` is both this package's error type and the wire format.**
    Its variants are the codes a Pairing_Failed packet carries, so a
    decode that failed has already worked out what to send back
    (section 3.5.5).
11. **A public key that does not validate never reaches you.**
    `peer_public_key` answers `None` before one has arrived, and a point
    off the curve has already failed the procedure with
    `DhKeyCheckFailed`. Handing a caller an invalid point is the
    invalid-curve attack.
12. **A responder's `begin` only asks.** It sends a Security_Request,
    which invites the initiator to pair or to encrypt with an existing
    bond. A peripheral cannot pair on its own authority.
13. **A `Confirm` value of -1 means this side types the passkey.** For
    Numeric Comparison the value is the six digits to display, and for
    Passkey Entry it is the passkey to display unless it is -1.
14. **The toolbox uses the specification's byte order**, which for SMP
    is least-significant byte first for addresses and nonces and
    most-significant first for the AES block. Its functions are total
    and have no error channel, because none of them can fail on inputs
    of the right width. The width of every argument is in its
    documentation comment.

## Running on a microcontroller

novo-lang lets a package state which of its modules can run on a device
with no heap allocator, and the compiler checks that claim on every
build. `tests/embedded_probe.nv` is that claim as a program that either
builds or does not.

**It does not build, and this package cannot be called from a device
today.** Every function in `toolbox` takes and returns `[u8]`, which is
a heap list, and the embedded tier allows no heap allocation. There is
no way to construct an argument for one of them there.

The fix is a change to these signatures rather than to the probe. Every
value the toolbox handles is fixed-width: 16 bytes for a block, 32 for a
public-key coordinate, 7 for an address, 3 for a prand.
[crypto-nv](https://novo-lang.org/packages/crypto-nv) is the published
package that runs on a device and keeps doing so, and it manages it with
a `@value` struct holding a true inline array, which lives on the
caller's stack with no heap cell. Version 0.1.0 is where those signatures change.
That is what a `0.0.x` release is for.

## What is not included

- **A radio, a clock, a random number generator and a bond store.** Each
  is an action the host performs. `NeedRandom` is the sharpest of them:
  a Security Manager that drew its own nonces would need the `[rand]`
  effect, and a package with that effect cannot go in firmware, which is
  the one place a peripheral's pairing has to run.
- **The pairing timeout.** Section 3.4 gives a procedure 30 seconds.
  This package has no clock, so the timer is the caller's, and `abort`
  is what it calls when the timer expires.
- **AES and the curve.** AES-128 and AES-CMAC are
  [crypto-nv](https://novo-lang.org/packages/crypto-nv), specified in
  FIPS 197 and RFC 4493. The P-256 curve is
  [p256-nv](https://novo-lang.org/packages/p256-nv), specified in
  FIPS 186-4. Both are useful to a reader who has never opened the Core
  Specification, and `f5` is not, which is the line the three packages
  are divided on.
- **Address resolution and privacy.** `ah` computes the hash that
  resolves a resolvable private address. Deciding which of a bond
  store's identity resolving keys to try it with is the host's work.
- **The channel.** Packets arrive as bytes and leave as bytes. Getting
  them to and from CID 0x0006 is l2cap-nv's work.

## Related packages

- [l2cap-nv](https://novo-lang.org/packages/l2cap-nv) is the layer
  below. It provides the channel, and `CID` here is its `CID_SMP`.
- [att-nv](https://novo-lang.org/packages/att-nv) is the sibling on CID
  0x0004. It reads and writes a peer's attributes, and its permission
  check is told whether the link is encrypted and authenticated, which
  is what this package arranges.
- [crypto-nv](https://novo-lang.org/packages/crypto-nv) is AES-128 and
  AES-CMAC, which every function in `toolbox` is a composition of.
- [p256-nv](https://novo-lang.org/packages/p256-nv) is the curve behind
  LE Secure Connections. Its `PublicKey` is the one type of another
  package in this one's surface.
- [hci-codec-nv](https://novo-lang.org/packages/hci-codec-nv) is the
  interface to a controller, and
  [ble-link-codec-nv](https://novo-lang.org/packages/ble-link-codec-nv)
  is the link layer below that.
- `std.crypto` in the standard library is OpenSSL. It is host only and
  has none of the Bluetooth compositions, so nothing here uses it.

## Tests

```bash
novo test tests/smp_tests.nv      # 21 tests against the signatures
```

The expected values are the ones the Bluetooth Core Specification
publishes in Volume 3, Part H, Appendix D, which is where the
implementation should take them from rather than from another stack.
What the suite asserts beyond them is the choreography: each test walks
one step of a pairing and checks that the action asked for is the one
the specification says comes next. A host driving this package should
never have to know anything the protocol did not tell it, and that is
the property these tests are written to catch.

The tests compile today and fail at run, each on the `not implemented`
panic that is its body. That is the expected state of an interface
release. They turn green in the order an implementation would want them
to, as bodies land.

## Implementation status

| Item | Implemented |
| --- | --- |
| `smp.CID` | yes (it is a constant) |
| `smp.new`, `.begin`, `.feed`, `.feed_random`, `.feed_user`, `.feed_link_encrypted`, `.abort` | no |
| `smp.state`, `.method`, `.is_authenticated`, `.peer_public_key` | no |
| `smp.encode_pdu`, `.decode_pdu`, `.pdu_opcode` | no |
| `smp.Failure.message` | no |
| `toolbox.c1`, `.build_c1_p1`, `.build_c1_p2`, `.s1`, `.ah` | no |
| `toolbox.f4`, `.f5_mackey`, `.f5_ltk`, `.f6`, `.g2`, `.h6`, `.h7` | no |

## Licence

Apache-2.0. See `LICENSE`.

<!-- docs/writing-a-readme.md is the style guide for this page. -->
