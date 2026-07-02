# Distributed URL Shortener - Engineering Workflow

## 1. Start With an Engineering Design Document (EDD)

Before writing any code, create:

# Project

Distributed URL Shortener

# Problem

Users need a reliable service to convert long URLs into short URLs and redirect users efficiently.

# Goals

* Generate unique short URLs
* Redirect users with low latency
* Support custom aliases
* Track click analytics
* Implement expiration policies
* Handle high read traffic
* Prevent abuse through rate limiting

# Non Goals (V1)

* Multi-region deployment
* URL malware scanning
* User teams and organizations
* QR code generation
* Kubernetes deployment
* Real-time analytics dashboard

# Tech Stack

Backend:

* FastAPI

Database:

* PostgreSQL

Cache:

* Redis

Infrastructure:

* Docker
* Nginx

# Why?

FastAPI:

* Fast development
* Async support

PostgreSQL:

* Strong indexing support
* Transactions
* Reliable relational model

Redis:

* Cache hot URLs
* Rate limiting

Docker:

* Reproducible deployment

Nginx:

* Reverse proxy
* Load balancing

# Success Metrics

* Redirect latency < 100ms
* Cache hit rate > 80%
* No duplicate short URLs
* Support 1000+ requests/minute locally

# Architecture

Client
↓
Nginx
↓
FastAPI
↓
Redis Cache
↓
PostgreSQL

If a feature is not inside this document, do not build it.
Avoid feature creep.


# Documentation Structure

docs/

├── architecture.md
├── threat-model.md
├── how-it-works.md
├── interview-notes.md
│
├── adr/
│   ├── 001-fastapi.md
│   ├── 002-postgresql.md
│   ├── 003-redis.md
│   ├── 004-short-url-generation.md
│
├── journal/
│   ├── day-01.md
│   ├── day-02.md
│
└── diagrams/
├── architecture-v1.png
├── architecture-v2.png

# Architecture Decision Records (ADR)

Example:

Decision:
Use PostgreSQL

Alternatives:

* MongoDB
* MySQL

Reason:

* Strong indexing
* Transaction support
* Better consistency guarantees

Consequences:

* More schema planning required

---

Decision:
Use Base62 encoding for short codes

Alternatives:

* UUID
* Random strings
* Hash-based IDs

Reason:

* Short URLs
* Human readable
* Efficient storage

Consequences:

* Requires collision prevention strategy

---

Decision:
Use Redis Cache

Alternatives:

* No cache
* In-memory cache

Reason:

* Reduce DB reads
* Improve redirect latency

Consequences:

* Cache invalidation complexity


# Claude Code Development Workflow

For Every Feature:

---

STEP 1 - Design

Example:

Design custom aliases.

Requirements:

* User chooses alias
* Alias must be unique
* Alias validation rules

Before coding:

1. Explain architecture
2. Explain database changes
3. Explain edge cases
4. Explain tradeoffs
5. List files to create

Wait for approval.

---

STEP 2 - Threat Model

Ask:

What can go wrong?

Check:

* Brute force enumeration
* Alias squatting
* URL injection
* Open redirects
* Spam abuse
* DDoS concerns

Document findings in:

docs/threat-model.md

---

STEP 3 - Architecture Review

Ask Claude:

Review this design.

Evaluate:

* Scalability
* Reliability
* Security
* Simplicity

Suggest only critical improvements.
Avoid overengineering.

---

STEP 4 - Implementation

Implement only approved design.

No surprise features.

---

STEP 5 - Testing

Create:

* Unit tests
* Integration tests
* Edge case tests

Examples:

* Duplicate alias
* Expired URL
* Missing URL
* Invalid URL
* Cache miss
* Cache hit

---

STEP 6 - Security Review

Ask:

Review this implementation as a security engineer.

Check:

* Input validation
* Rate limiting
* URL validation
* SQL injection
* Secret handling
* Authentication

Provide vulnerabilities and fixes.

---

STEP 7 - Documentation Update

Update:

architecture.md
how-it-works.md
journal/day-x.md

Example:

Implemented:

* Redis caching

Learned:

* Cache-aside pattern

Problem:

* Stale cache entries

Solution:

* TTL-based invalidation

---

STEP 8 - Interview Notes Update

For every feature answer:

Why PostgreSQL?

Why Redis?

Why not MongoDB?

Why cache redirects?

How are collisions prevented?

How would you scale to 10 million URLs?

How would you scale to 100k requests/sec?

What was the hardest bug?

What would you improve in V2?

---

System Diagrams

Update after every major feature:

V1:
Client → API → Database

V2:
Client → Nginx → API → Database

V3:
Client → Nginx → API → Redis → Database

V4:
Client → Nginx → API → Redis → Database
↓
Analytics Worker

---

Most Important Document

docs/how-it-works.md

Request Flow

Create Short URL

1. User submits URL
2. Validate URL
3. Generate short code
4. Store mapping
5. Return shortened URL

Redirect Flow

1. User visits short URL
2. Check Redis
3. If hit → redirect
4. If miss → query PostgreSQL
5. Cache result
6. Redirect user

Analytics Flow

1. Redirect occurs
2. Event recorded
3. Worker processes event
4. Statistics updated

If you can explain these flows clearly, you understand the system.


I'd build the URL shortener in three phases:

Core service — URL creation, redirects, PostgreSQL.
Performance layer — Redis caching, rate limiting, analytics worker.
Scale layer — Docker, Nginx load balancing, stress testing, architecture improvements.

That progression gives you a clean story in interviews: first I built it, then I optimized it, then I scaled it. That's much stronger than starting with every tool under the sun on day one.

---

# Addendum: Scope Amendment — Minimal Frontend

**Added 2026-07-02, requested directly by the user in-session** (the EDD's "if a
feature isn't in this doc, don't build it" rule is enforced against silent scope
creep, not against an explicit ask from the person who owns this document).

**New goal:** a minimal frontend — no framework, no build step:
- A page to submit a URL (with optional custom alias / expiry) and receive the
  short link.
- A page listing all **live** (non-expired) URLs: short URL, original URL,
  expiration date.

**Explicitly still non-goals:** authentication/authorization, a design system,
client-side routing/SPA framework, and anything not needed for the two pages
above. See `docs/adr/012-frontend.md` for the implementation and
`docs/threat-model.md` for the resulting (unauthenticated data exposure) risk
this introduces.

