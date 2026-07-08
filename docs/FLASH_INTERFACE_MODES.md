# Flash Interface Modes

## Mode A: RAM-Emulation Interface

Flash appears like memory.

Pros:

- compatibility
- existing cache hierarchy can be used
- incremental porting

Cons:

- performance cliff on random access
- fragile tail latency
- may hide bad behavior
- hard to guarantee p99

This mode is useful for functional bring-up and broad compatibility.

---

## Mode B: Stream-to-Scratchpad Interface

Flash exposes explicit page or bundle streaming into scratchpad and DRAM.

Pros:

- deterministic
- high bandwidth potential
- better sequentiality
- explicit control

Cons:

- requires code, runtime, and compiler changes
- less compatible

This is the preferred performance-oriented model.

---

## Mode C: Hybrid Interface

Hybrid mode combines both:

- RAM-emulation for compatibility and cold start
- explicit stream API for optimized path
- trace-guided migration from RAM mode to stream mode

This is important because it offers a practical adoption path.

> RAM-emulation gets the model running. Stream-to-scratchpad gets the model fast.
