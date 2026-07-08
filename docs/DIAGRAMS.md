# Diagrams

## High-Level Memory Hierarchy

```mermaid
flowchart TD
    A[AI Compute Engine] --> B[SRAM Tier<br/>Hot token tiles<br/>Active KV<br/>Decode scratch]
    B --> C[DRAM / LPDDR Tier<br/>Warm KV<br/>Prefetch window<br/>Staging buffers]
    C --> D[NVMe SSD Flash Tier<br/>Cold KV<br/>Model pages<br/>MoE experts<br/>Long context]
```

---

## Critical Path vs Hidden Path

```mermaid
flowchart LR
    subgraph Critical Path
        A[SRAM] --> B[Compute] --> C[Output Token]
    end
    subgraph Hidden Path
        D[SSD Flash] --> E[DRAM Staging] --> F[SRAM Promotion]
    end
    F -. ready before use .-> A
```

---

## Runtime Components

```mermaid
flowchart TD
    A[Token Driver] --> B[Residency Manager]
    A --> C[Prefetch Planner]
    C --> D[Flash IO Engine]
    D --> E[DRAM Buffer Pool]
    E --> F[Decompression Workers]
    F --> G[SRAM Manager]
    B --> G
    G --> H[Compute Engine]
    B --> I[Metrics + Policy Engine]
    I --> C
```

---

## Object State Machine

```mermaid
stateDiagram-v2
    [*] --> FLASH_ONLY
    FLASH_ONLY --> FLASH_TO_DRAM_IN_FLIGHT
    FLASH_TO_DRAM_IN_FLIGHT --> DRAM_RESIDENT
    DRAM_RESIDENT --> DRAM_TO_SRAM_IN_FLIGHT
    DRAM_TO_SRAM_IN_FLIGHT --> SRAM_RESIDENT
    SRAM_RESIDENT --> DRAM_RESIDENT
    DRAM_RESIDENT --> COMPRESSED_COLD
    COMPRESSED_COLD --> FLASH_ONLY
```

---

## KV Cache Tiering

```mermaid
flowchart TD
    A[KV Cache] --> B[Hot KV]
    A --> C[Warm KV]
    A --> D[Cold KV]
    B --> E[SRAM / DRAM]
    C --> F[DRAM]
    D --> G[Compressed Flash]
    H[Attention Scores] --> B
    H --> C
    H --> D
```

---

## MoE Expert Tiering

```mermaid
flowchart TD
    A[Router / Predictor] --> B[Top-K Likely Experts]
    B --> C[DRAM Prefetch]
    C --> D[Selected Expert Tiles]
    D --> E[SRAM]
    E --> F[Expert Compute]
    G[Cold Experts] --> H[SSD Flash]
    H --> C
```
