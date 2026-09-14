# StudioNet evidence

## Finalized deployment receipts

The Studio network selector displayed **GenLayer Studio, chain 61999 · local** and was selected immediately before each deployment transaction. Both deployments reached `FINALIZED` in Studio.

| Contract | Address | Finalized transaction hash |
|---|---|---|
| Interlock | `0xa51c5E2602a5BF489e9A15dccc04dE1E461a61C4` | `0x50d7acf99e4401e53e412198ae5ec8bcabe534e8139e0ed396f4b208885ebdbd` |
| ProtectedResource (deployed with the Interlock address) | `0x00c010Ab0c746c88CAB24f0523B75e68DCFc140b` | `0xe560813006d8d17029589e10698ae867c4597c50f7c7340010ca768452f92b91` |

Interlock's finalized deployment page linked to `https://explorer-studio.genlayer.com/address/0xa51c5E2602a5BF489e9A15dccc04dE1E461a61C4`. ProtectedResource's finalized deployment page linked to `https://explorer-studio.genlayer.com/address/0x00c010Ab0c746c88CAB24f0523B75e68DCFc140b`.

## Live lifecycle status

No live resource or intent lifecycle evidence is claimed. Studio's onboarding states that the current Studio does not support contract-to-contract interactions. That prevents proving the typed `IInterlock(...).view().is_grant_active(...)` invocation and the downstream consumer behavior in the requested environment. Deployment of ProtectedResource only proves its constructor and storage initialization completed; it does not prove a cross-contract call.

| Required live demo evidence | Status |
|---|---|
| Chain ID 61999 for both deployment transactions | Confirmed in the selected Studio network selector before each deployment |
| Resource ID and definition hash | Not executed |
| Non-owner `submit_intent` rejection | Not executed |
| Intent IDs, actors, and exact action hashes | Not executed |
| Pair relation and immutable decision hash | Not executed |
| CANCEL blocked while DISPATCH is active | Not executed |
| CANCEL grant after blocker completion or expiry | Not executed |
| ProtectedResource reject before a live grant | Not proven |
| ProtectedResource accept after a live grant | Not proven |
| Replay rejection after live execution | Not proven |

The Direct Mode suite verifies the protocol and consumer boundary locally. The live reviewer demo remains incomplete until StudioNet supports and exposes the required contract method and cross-contract transactions. No transaction hashes, resource identifiers, or model results are fabricated here.
