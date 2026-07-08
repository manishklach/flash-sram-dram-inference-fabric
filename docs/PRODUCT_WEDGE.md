# Product Wedge

## 1. Goal

Define the smallest credible product that expresses the architecture's value in the market.

The wedge should be narrow enough to execute, but important enough to create real revenue and learning.

---

## 2. Recommended First Product

### Long-Context Private Inference Appliance

A system for enterprise and sovereign deployments that:

- serves long-context RAG workloads
- supports many warm and cold sessions
- reduces dependence on very large premium-memory pools
- keeps private data on customer-controlled infrastructure

This product aligns well with the architecture because:

- long-context KV tiering is one of the strongest technical fits
- enterprise RAG often has predictable retrieval staging opportunities
- on-prem buyers care about total cost and privacy
- many deployments have bursty usage with cold resumable state

---

## 3. Narrow Technical Scope for v1

Do not try to solve everything in version one.

Recommended v1 scope:

- decode-time KV tiering
- prefill-time retrieval staging
- DRAM-resident hot weights
- flash-resident cold KV and session state
- optional flash-resident cold experts for selected MoE models

Avoid in v1:

- universal full-weight decode streaming
- arbitrary random-attention guarantees
- training workloads
- all runtimes and all accelerators

---

## 4. Buyer and User

Primary buyer:

- infrastructure leader
- CIO / CTO for private AI deployment
- OEM partner building enterprise AI boxes

Primary user:

- platform engineer
- inference systems engineer
- enterprise AI team operating private models

---

## 5. Main Value Proposition

For the right workloads, the product aims to offer:

- lower memory-system cost
- longer practical context windows
- more resumable sessions per system
- private deployment on commodity infrastructure
- better economics for cold-state-heavy inference

This is not a promise of universal peak throughput leadership. It is a promise of better memory economics for selected inference workloads.

---

## 6. Early Proof Points Needed

The wedge becomes real when the repo can demonstrate:

- long-context latency that stays stable under target traces
- lower premium-memory requirement than a baseline deployment
- resumable session behavior with acceptable user-visible delay
- sequential read dominance under trace-guided layouts
- predictable failure boundaries when workloads become too random

---

## 7. Expansion Path

After the first wedge, expansion could move toward:

- larger enterprise appliance lines
- software-only runtime licensing
- MoE-serving optimization stacks
- OEM integrations with accelerator vendors
- inference memory orchestration for edge AI clusters

The wedge is the first beachhead, not the full market.
