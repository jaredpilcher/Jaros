# Intent

To enable operators and developers to dynamically extend the Execution Plane with custom actions/tools (such as specialized PostgreSQL query executors, system utilities, or APIs) without modifying the core Jaros OS codebase. Custom tools are defined as standard Python classes dropped into a watched folder, carrying their own namespaced action names, custom parameter validation gates, and safe execution handlers. The core Harness registers these tools dynamically, maps their namespaces to security permissions, and dynamically authorises execution based on the agent's assigned role. 

This preserves the **Prime Directive** flawlessly:
1. The agent (Reasoning Plane) remains completely decoupled, emitting only inert JSON decisions.
2. The custom tool (Execution Plane) executes deterministically on the host under the complete control and sandboxing of the Harness.
3. The custom validation gate runs pure, side-effect-free checks to fail-closed on malformed parameter payloads.

---
## Traceability
- [Creates REQ-1]
- [Creates REQ-2]
- [Creates REQ-3]
- [Creates REQ-4]
