# Intent

Allow exactly two channels for inter-agent communication — rigid typed queues and a shared file system — and forbid everything else. No agent may address or call another directly; all cross-agent flow is observable as queue messages or file system artifacts, and the absence of direct calls is enforced structurally. This is the Prime Directive's communication tenet, held as an architectural constraint.
