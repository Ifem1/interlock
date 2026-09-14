# Reviewer demo

Target: **StudioNet, chain ID 61999**.

This walkthrough is the intended end-to-end demonstration. At the verification date recorded in `STUDIONET_EVIDENCE.md`, Studio's onboarding stated that it does not support contract-to-contract interactions. The deployed contracts therefore do not yet have a complete live lifecycle proof. Do not present the unexecuted steps below as live evidence.

## Lifecycle to demonstrate when supported

Create one order-like resource with a frozen definition describing the order lifecycle, allowed state transitions, capacity assumptions, and the meaning of fulfilment/cancellation. Record its resource ID and `definition_hash`.

First call `submit_intent` from an account other than the resource owner. It must revert. Then, as owner/gateway, admit two `READ` actions with explicit actors. Resolve both; they should become `GRANTED` deterministically without semantic classification. Complete both.

Admit `DISPATCH` as `WRITE` and resolve it to `GRANTED`. Admit `CANCEL` as `WRITE` and resolve while dispatch is active. Record both intent IDs, explicit actors, exact canonical action hashes, and the resource hash. The result should be `CONFLICTS` (ideally `WRITE_OVERLAP` plus `ORDER_SENSITIVITY`) and the cancel intent should be `BLOCKED`. Read `get_pair_decision` twice and verify its immutable `decision_hash` is unchanged.

As the actor or resource owner, complete DISPATCH (or let its lease expire, then call permissionless `expire_intent`). Resolve CANCEL again; its former blocker is terminal, so CANCEL should be `GRANTED` if no other conflict exists.

Call `ProtectedResource.execute` with the exact intent ID, pinned resource hash, canonical action hash, and payload hash. Before a valid grant it must reject. After the grant it must accept once, then reject the same action hash on replay. The consumer must itself derive or verify the action hash from the executable action. Interlock makes no claim about the truth of an off-chain payload.

## Evidence

Only finalized chain transactions belong in `STUDIONET_EVIDENCE.md`. Direct Mode test results are local evidence and must remain clearly distinguished. The current documented Studio limitation prevents claiming the end-to-end scenario or typed IC-to-IC call as live verified.
