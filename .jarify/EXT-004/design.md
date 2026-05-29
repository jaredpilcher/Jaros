# Design — Interchangeable LLM Adapter

The LLM sits behind one interface. Callers know only `LlmClient`; the concrete model is chosen by configuration and can be swapped freely.

## Indirection

```text
   callers (agents' reasoning)
            |
            v
     +--------------+        config selects
     |  LlmClient   |<----------------------------+
     | (interface)  |                             |
     +------+-------+                             |
            |                                     |
   +--------+---------+----------------+          |
   v                  v                v          |
[Adapter A]      [Adapter B]      [Adapter C] ----+
(model X)        (model Y)        (model Z)
```

## What crosses the boundary

```text
   request  --> LlmClient.complete() --> response (data only)

   response is consumed by reasoning, which emits a Decision (EXT-001).
   The LLM never calls transition(...) and never holds system handles.
```

## Invariants

- Callers depend on `LlmClient` only; no provider type escapes the adapter.
- Adapter selection is configuration-driven; swapping requires no caller/harness code change.
- The model returns outputs; it never drives control flow or state transitions.
