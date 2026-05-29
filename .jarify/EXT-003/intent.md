# Intent

Run agents as lightweight computing threads, not bloated microservices. Spawning an agent must be as cheap as starting a thread — no port, no deployment, no per-agent infrastructure — so that many agents can run concurrently and a single agent's failure is contained rather than catastrophic. This realizes the Prime Directive's insistence that agents are threads, not services.
