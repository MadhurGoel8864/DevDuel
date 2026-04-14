# Bidding Redis Pub/Sub Rollout Checklist

## Configuration
- Set `BIDDING_REDIS_PUBSUB_ENABLED=true` in environment for target deployment.
- Ensure all backend instances point to the same Redis server.
- Keep websocket ingress sticky-session optional; pub/sub fanout should work regardless.

## Pre-Deployment Verification
- Deploy with feature flag disabled first and verify baseline bidding flow.
- Confirm logs include no `bidding-pubsub` errors after service boot.
- Validate websocket `SYNC` payload still works for reconnecting clients.

## Staging Validation (Multi-Instance)
- Run at least 2 backend instances connected to one Redis.
- Connect websocket client A to instance 1 and client B to instance 2.
- Start auction and verify both clients receive `AUCTION_STARTED`.
- Place bid through one instance and verify both clients receive `NEW_HIGHEST_BID`.
- Finish auction (timer or force-end) and verify both clients receive `AUCTION_FINISHED`.
- Verify each event appears once per client (no duplicates).

## Failure Scenarios
- Restart one backend instance during active auction; verify it resumes receiving events after boot.
- Temporarily interrupt Redis connectivity; verify subscriber reconnects and logs backoff attempts.
- Reconnect websocket client and verify `SYNC` heals transient missed events.

## Production Rollout
- Enable feature flag for a small production slice.
- Monitor logs for publish failures and subscriber loop errors.
- Gradually enable flag for all instances.
- After stable period, remove fallback-only assumptions in runbook.
