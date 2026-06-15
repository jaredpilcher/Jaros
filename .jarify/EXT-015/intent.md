# Intent

When a swarm of agents does something wrong, two questions must be answerable by
*recorded fact*, not guesswork: **can we reproduce it**, and **which agent caused
it**. EXT-015 makes both true at the swarm scale. Because every accepted `Decision`
is already recorded with its `source` agent into one ordered, durable log, the
whole hive can be replayed through the deterministic executor to byte-identical
state with no model call, and any divergence or failure can be attributed to the
exact decision — and the exact agent — that produced it. The decision log is made
tamper-evident (hash-chained) so that account of who-did-what is itself
trustworthy. This realizes the Prime Directive's apex purpose
[PRIME-001 / P5] — swarm reproducibility and accountability — by extending the
single-run replay (EXT-002 / REQ-6) to a multi-agent run, with no new
infrastructure: still just files and threads.
