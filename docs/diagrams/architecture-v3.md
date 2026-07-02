# Architecture v3 (Phase 3)

> PNG diagrams aren't generated in this repo; this Mermaid source is the
> versioned diagram. Bump to `architecture-v4` when the topology changes.

```mermaid
flowchart TD
    Client([Client])

    subgraph Edge
        Nginx[Nginx reverse proxy<br/>X-Real-IP · limit_req · LB]
    end

    subgraph App[FastAPI app - non-root container]
        API[Routes<br/>rate limiting · logging · validation]
    end

    Worker[Analytics Worker<br/>python -m app.worker]

    subgraph Data
        Redis[(Redis<br/>cache · rate-limit buckets · clicks:stream)]
        PG[(PostgreSQL<br/>urls · clicks)]
    end

    Client --> Nginx --> API
    API -- cache-aside --> Redis
    API -- read/write --> PG
    API -- XADD click --> Redis
    Redis -- XREADGROUP --> Worker
    Worker -- batch INSERT --> PG
    API -- SELECT nextval + INSERT --> PG
```

## History

- **v1:** Client → FastAPI → PostgreSQL
- **v2:** Client → FastAPI → Redis (cache-aside) → PostgreSQL
- **v3 (this):** Client → Nginx → FastAPI → Redis/PostgreSQL, + analytics worker
  draining `clicks:stream` → PostgreSQL
