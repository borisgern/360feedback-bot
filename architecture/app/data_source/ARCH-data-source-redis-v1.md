---
id: ARCH-data-source-redis
title: "Data Source: Redis"
type: component
layer: infrastructure
owner: @team-backend
version: v1
status: current
created: 2025-06-27
updated: 2025-06-27
tags: [redis, cache, fsm, data-source, infrastructure]
depends_on: []
referenced_by: []
---
## Context
Redis is used as a fast, in-memory data store for three primary purposes:
1.  **Application Data Caching:** To reduce latency and load on Google Sheets (e.g., caching the questionnaire).
2.  **FSM Storage:** To persist the state of user interactions with the bot across multiple messages (e.g., during cycle creation or survey taking).
3.  **Application State Storage:** Storing live data such as `FeedbackCycle` objects and pending notifications.

## Structure
- **Service Wrapper:** `backend/src/storage/redis_storage.py::RedisStorageService` provides a high-level, model-aware interface over the raw Redis client.
- **FSM Storage:** `aiogram.fsm.storage.redis.RedisStorage` is used directly by the `aiogram` Dispatcher for FSM state management.
- **Client Library:** `redis.asyncio` is used for non-blocking communication with the Redis server.

### Key Patterns:
- **Pydantic Models:** `RedisStorageService` serializes Pydantic models to JSON strings before storing them and deserializes them back upon retrieval (`set_model`/`get_model`).
- **Key Naming Convention:**
  - `cycle:{cycle_id}`: Stores a `FeedbackCycle` object.
  - `questionnaire_v2`: Caches the `Questionnaire` object.
  - `employee_tg_id:{employee_id}`: Maps an employee's business ID to their Telegram ID.
  - `pending_notifications:{employee_id}`: A Redis set of `cycle_id`s for which an employee has a pending invitation.

## Behavior
- `set_model`/`get_model`: Stores/retrieves Pydantic models.
- `set_value`/`get`: For simple key-value pairs.
- `add_to_set`/`get_set`: For managing sets, used for pending notifications.
- `delete_key`: Used to clear pending notifications after they are delivered.
- `get_keys_by_pattern`: Used to count active cycles (a simplification).

## Evolution
### Planned
- The key schema may evolve as new features are added.
- The `get_active_cycles_count` implementation could be made more robust by using a dedicated Redis set for active cycle IDs.

### Historical
- v1: Initial implementation with Pydantic model support and basic Redis operations.
