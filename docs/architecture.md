# Architecture Notes

## Thesis

Inference systems can treat flash as a capacity tier if the runtime reliably promotes data through DRAM into SRAM before compute needs it.

## Working model

- SRAM is reserved for the current token's active working set.
- DRAM absorbs prediction error and stages near-future data.
- Flash stores cold state and bulk capacity.

## Runtime loop

For each decode step:

1. Serve the current working set from SRAM.
2. Consume predicted next-use state already staged in DRAM.
3. Stream future pages from flash to DRAM asynchronously.
4. Promote the hottest subset from DRAM to SRAM just ahead of use.

## Initial focus areas

- latency budget accounting across tiers
- DRAM staging window sizing
- KV and expert temperature models
- sequential flash-friendly layouts
- prediction miss penalties
