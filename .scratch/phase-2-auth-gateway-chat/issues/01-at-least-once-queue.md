Status: open
Type: feature
Acceptance: worker crash mid-job -> job redelivered by reaper; integration test with BLMOVE

# At-least-once job delivery

From Phase 1 retro #6. Use BLMOVE into a per-worker processing list, ack on success, reaper re-queues stale items.
