"""Mint a Clerk MCP turn token for the pi spike.

Run from backend/ so `app.*` imports and .env settings resolve:
    cd backend
    python ../spikes/pi-corpus-spike/mint_token.py
Requires SPIKE_USER_ID and SPIKE_PROJECT_ID env vars (a real user who
owns a real project with ingested documents).
"""
import os
import uuid

from app.mcp_bridge.tokens import mint_turn_token

token = mint_turn_token(
    user_id=uuid.UUID(os.environ["SPIKE_USER_ID"]),
    project_id=uuid.UUID(os.environ["SPIKE_PROJECT_ID"]),
    ttl_seconds=3600,
)
print(token)
