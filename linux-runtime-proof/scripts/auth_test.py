import os, sys
from hai_agents import Client
from hai_agents.environment import HaiAgentsEnvironment

key = os.environ.get("HAI_API_KEY")
print(f"key present: len={len(key)} prefix={key[:4]}…")
for env in (HaiAgentsEnvironment.US, HaiAgentsEnvironment.EU):
    print(f"\n=== {env.name} {env.value} ===")
    client = Client(api_key=key, environment=env, timeout=30)
    try:
        print("  token quota:", client.quota.get_token_quota())
    except Exception as e:
        print("  quota failed:", type(e).__name__, str(e)[:300])
    try:
        client.agents.list()
        print("  agents.list: OK (authenticated)")
    except Exception as e:
        print("  agents.list failed:", type(e).__name__, str(e)[:300])
