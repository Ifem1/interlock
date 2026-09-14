# Interlock — Intelligent Contract submission

## One-line description

A reusable semantic concurrency-control primitive that safely parallelizes commuting autonomous-agent operations while serializing conflicting or ambiguous operations against a shared resource.

## Problem

Conventional locks work when developers already know the exact resource keys and conflict matrix. Autonomous agents increasingly express effects semantically. Two operations can touch different fields yet still conflict in meaning (`dispatch` vs `cancel`), while two writes may be independent (`update internal note` vs `update printable label`).

A global mutex is safe but destroys parallelism. Optimistic parallel execution without a semantic conflict layer can create contradictory side effects.

## Primitive

Interlock gives every shared resource a frozen semantic definition. Only the resource owner (or an owner-controlled gateway) may admit intents, preventing arbitrary lock-DoS. Each intent binds an explicit actor, exact action hash, access mode, semantic description, queue TTL, and grant lease.

The deterministic scheduler grants an intent only when it commutes with all active grants and all earlier open intents.

Where commutativity cannot be decided mechanically, GenLayer consensus independently classifies the pair as:

```text
COMMUTES
CONFLICTS
AMBIGUOUS
```

Ambiguity fails closed.

## Why consensus is substantive

Validators independently re-derive the relation and bounded conflict mask from the same frozen resource definition and intent pair. They do not merely validate JSON or trust the leader's rationale.

Two common cases bypass LLM reasoning entirely:

- READ + READ => COMMUTES
- EXCLUSIVE + anything => CONFLICTS

The LLM never controls admission, actor authorization, queue priority, lease duration, expiry, action identity, resource versioning, or state transitions.

The leader's free-form explanation is also not trusted state: only the bounded relation/mask are consensus fields, and the stored pair summary is derived deterministically from them.

## Stateful protocol mechanics

- owner/gateway-only intent admission
- explicit actor binding
- commuting FIFO scheduler
- active-grant concurrency set represented by open intent state
- immutable exact-pair decision cache
- resource generation/definition hashes
- exact action-hash uniqueness per resource
- bounded queue and scan work
- emergency resource pause plus permissionless queue/grant expiry
- actor-or-owner cancellation/completion
- consumer-facing actor/action/resource-pinned grant view

## Reuse

A consumer contract can gate a state transition on:

```text
is_grant_active(intent_id, resource_hash, action_hash, actor)
```

The included `ProtectedResource` implements that boundary and adds local one-time replay protection. The 30-test Direct Mode suite exercises reject/accept/replay behavior through a controlled interface stub, and GenVM lint accepts the typed interface declaration. StudioNet Studio currently states that it does not support contract-to-contract interactions, so this submission does not claim that the live IC-to-IC call or consumer lifecycle has been proven on chain 61999. Production gateways/consumers must compute or verify the action hash from a canonical executable action representation and domain-separate it to the intended consumer.

## Intended use cases

- order cancellation vs fulfilment
- revoke vs execute
- delete vs update
- rotate credential vs open session
- close account vs charge account
- shared autonomous-agent configuration changes
- capacity-affecting agent operations

## What it does not do

Interlock is not an authorization system, escrow, dispute resolver, workflow engine, or source oracle. The admitting owner/gateway decides which actors/actions are eligible. Interlock controls only whether already-admitted operations may safely overlap in time against the same shared resource.

## Why there is no frontend

Interlock is infrastructure, not a product flow. A frontend would move the submission toward the Projects category and add unrelated surface area.

## Network

Prepared only for **StudioNet chain ID 61999**.

## Live verification boundary

Interlock has a finalized deployment on Studio chain ID 61999 at the address recorded in `docs/STUDIONET_EVIDENCE.md`. The earlier ProtectedResource deployment predates the corrected Interlock bytecode and must not be presented as the current paired deployment. Studio's current UI says it does not support contract-to-contract interactions, so the corrected ProtectedResource redeployment and consumer IC-to-IC call remain unproven until Studio permits them.

