# How It Works

## Create Short URL

1. Client `POST /shorten` with `{ "url": "...", "custom_alias": "..." (optional) }`.
2. Pydantic validates the URL: only `http`/`https` schemes, max 2048 chars.
3. If `custom_alias` is provided:
   - Regex check: 4–32 chars, `[a-zA-Z0-9_-]`.
   - Reserved-word check against `RESERVED_WORDS` set.
   - Insert row; UNIQUE constraint on `short_code` rejects duplicates → 409.
4. Otherwise:
   - `SELECT nextval('urls_id_seq')` to reserve an ID.
   - Encode the ID to Base62, left-padded to 7 chars.
   - Insert row with that `id` and `short_code`.
5. Return `{ short_url, short_code, long_url }` where `short_url = BASE_URL + "/" + short_code`.

## Redirect

1. Client `GET /{code}`.
2. Look up row by `short_code` (indexed).
3. If miss → 404.
4. If hit → 301 redirect to `long_url`. (301 = permanent, lets browsers cache and reduce load.)

## Why 301?

Mappings are immutable in V1, so permanent redirect is correct semantically and reduces repeat traffic. Tradeoff: harder to "change a target" later — accepted.

## Why Base62 of auto-increment ID?

- Simple — no collision logic needed; UNIQUE constraint on the column is a safety net.
- Compact — 7 chars covers ~3.5 trillion IDs.
- Tradeoff: codes are guessable/enumerable. Documented in `threat-model.md`; rate limiting (Phase 2) is the primary mitigation.
