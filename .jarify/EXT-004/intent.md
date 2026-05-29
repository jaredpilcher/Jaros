# Intent

Treat the LLM as a pluggable application, never as the foundation. All model access flows through one narrow interface; the concrete model is chosen by configuration and can be swapped with zero changes to the harness or state machine. The model produces outputs only — it never holds control flow or drives state. This is the Prime Directive's "interchangeable application" tenet made concrete.
