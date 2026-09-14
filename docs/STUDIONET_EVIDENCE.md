# StudioNet live evidence

Target network: **StudioNet, chain ID 61999** (`https://studio.genlayer.com/api`). The Studio selector showed `GenLayer Studio chain 61999 · local` immediately before each transaction below.

## Deployments (FINALIZED, SUCCESS)

- Interlock: `0xA23e95942E03Cb63614C6cB212A8C2b56F9DE061`
  - tx `0xacfa75c76d7926e658abbf501dd83120fdd247d482f096ed59cf355b69349b9a`
- ProtectedResource, constructed with that Interlock address: **previous deployment remains valid only for the prior bytecode**; the corrected Interlock redeployment requires a fresh consumer deployment before claiming live IC-to-IC compatibility.

## Corrected core lifecycle (Interlock)

- Resource creation tx: `0x511aadaee9c914dc650cc606d44508ec4365c31d83dea42152e2dd43f19cf0b7`, FINALIZED/SUCCESS; returned resource ID `1`.
- Resource definition hash: `51dd7d9acf550103057daea4d0f21741c9c5c2c605af7d116ba0cae448629b66`.
- Owner: `0x38D2270Ba7224b7771A30fE20Ec4A12616d15DF0`.
- Explicit actor: `0x9A91f6fe04700744fD3838cA2c63161b261Cb919`.
- Non-owner admission tx: `0x034ea2e3d9e0faf3b05d2483d3c248fbf8425c9e302347bc01dbb7e57d9634a6`, FINALIZED/ACCEPTED with Result `ERROR`: `EXPECTED: only resource owner may admit intents`.
- Owner admission of DISPATCH returned intent ID `1`; tx `0x228cfae053473c51732d06c11d84271b2f38d169f88a5680ba88c6e456850a52`, FINALIZED/SUCCESS.
- Owner admission of CANCEL returned intent ID `2`; tx `0xe88dcc843d4188709720d039c2cd9eb8f469fa206e80d3210ef949870d1d6782`, FINALIZED/SUCCESS.
- Canonical action hashes (domain `interlock-action/v1`, resource ID `1`, resource hash above): DISPATCH `0a41470c9f19ecb4d9a244b078308bb2eecf62c2777939703c8dc8ffd5d9d513`; CANCEL `d2cccaac729de07d0281db1c312865558d910c62c0454faccc6eb4f0d6dccf8e`.
- DISPATCH resolve tx `0x0ab62edcad35e1886b481324582520455fc085a0f54d83fe2459b09024a02601` reached consensus and finalized; DISPATCH became GRANTED.
- CANCEL resolve tx `0xbb6edb40ba45a916299590f09134d8df7e81ccc7b313c5f81c9fa09067707508` is still in Studio validator rotation at the time of this edit; no final relation or grant claim is recorded until its receipt visibly finalizes.

## Consumer boundary

Studio’s onboarding still states that contract-to-contract interactions are unsupported. The corrected consumer deployment and `ProtectedResource.execute` reject/accept/replay path therefore remain unproven live. Direct Mode covers the typed interface boundary with a controlled stub; no IC-to-IC claim is inferred from deployment alone.
