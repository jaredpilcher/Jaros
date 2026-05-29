from jaros.core import create_decision

KIND = "custom_agent"

def build(llm):
    class CustomAgent:
        def decide(self, context):
            # Printing inside the container will clearly demonstrate the agent executing in the Docker logs
            print(f"[CustomAgent] Deciding with context: {context}", flush=True)
            return [
                create_decision(
                    id="custom-dec-1",
                    source="custom_agent",
                    kind="advance",
                    payload={
                        "events": ["start", "complete"],
                        "note": "Custom agent executed inside Docker!",
                        "artifact_path": "artifacts/custom_agent_result.json"
                    }
                )
            ]
    return CustomAgent()
