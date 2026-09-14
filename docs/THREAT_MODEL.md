# Threat model

## Arbitrary caller attempts lock denial-of-service

If anyone could enqueue a long-lived conflicting intent, a public lock manager could be griefed cheaply.

Mitigation: only the resource owner (or an owner-controlled gateway contract) can admit intents. Interlock deliberately leaves actor authorization policy outside this primitive.

## Owner/gateway understates an operation

The admitting owner may describe a destructive operation as harmless. Interlock cannot cryptographically prove that a natural-language description matches arbitrary external execution.

Mitigation: every grant binds an exact `action_hash`. Production gateways/consumers must define a canonical action encoding and ensure that hash commits to the actual target, method, arguments, nonce/domain, and any other execution-critical fields. Interlock makes no truth claim beyond the frozen admitted intent.

Trusted-mode assumption: the resource owner or owner-controlled gateway is trusted to admit only actors and actions it intends to coordinate, and to derive each `action_hash` from the canonical executable action. Interlock prevents arbitrary callers from injecting locks and enforces the pinned hashes, but it cannot detect a trusted owner deliberately admitting a misleading description or an incorrect action preimage.

The example consumer has only been exercised in Direct Mode through a controlled interface stub. Studio's current UI reports that it does not support contract-to-contract interactions. The live call is therefore an explicit unverified boundary, not evidence that deployment alone established composability.

## Owner rewrites semantics after admission

Mitigation: resource updates are impossible while `open_count > 0`; every intent pins the current `definition_hash`.

## Leader proposes `COMMUTES` for conflicting operations

Mitigation: validators independently re-run the same bounded classification. Exact agreement on relation and conflict mask is required.

## Leader supplies manipulative rationale

Mitigation: free-form model rationale is excluded from equivalence and is not persisted as trusted pair state. The stored pair summary is derived deterministically from the relation and conflict-mask names.

## Model is uncertain but guesses

Mitigation: the prompt requires conservative `AMBIGUOUS`; malformed outputs canonicalize to ambiguity; ambiguity blocks concurrency.

## Actor holds a grant forever

Mitigation: every grant has a bounded lease and anyone can call `expire_intent` after the deadline.

## Blocked intent holds FIFO forever

Mitigation: pending/blocked intents have queue TTLs; the resolver clears stale blockers permissionlessly.

## Later conflicting work starves older work

Mitigation: a later intent must commute with every earlier open intent before it may be granted.

## Later work bypasses older work that genuinely commutes

Allowed by design. This is why Interlock provides more concurrency than a global mutex while retaining FIFO priority for conflicts.

## Pair relation changes after model upgrade

Mitigation: an existing exact pair decision is immutable. A new action or new resource generation creates new IDs/hashes and may receive a new classification.

## Consumer reuses a still-active grant

Interlock exposes grant validity, not global consumption across arbitrary consumers. `ProtectedResource` enforces local one-time `action_hash` execution. Production consumers must implement equivalent replay protection and should domain-separate action hashes to the intended consumer.

## Grant used for a different executable action

Out of scope unless the integrating system computes/verifies `action_hash` from a canonical action representation. The example consumer demonstrates grant binding but does not claim to prove arbitrary off-chain payload truth.

## Cross-resource hidden conflict

Out of scope. Interlock coordinates intents registered against the same `resource_id`. Systems requiring multi-resource atomicity need a higher-level coordinator.
