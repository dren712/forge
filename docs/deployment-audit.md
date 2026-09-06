# FORGE Deployment Audit — Supabase PostgreSQL Readiness

## Executive Summary
This audit evaluates the database layer of **FORGE** to prepare the platform for production deployment using **Supabase Managed PostgreSQL**. The evaluation confirms that the codebase is fundamentally decoupled from SQLite specifics through SQLAlchemy 2.0 async abstractions and can transition to PostgreSQL with zero core architectural rewrites.

---

## 1. Current Database & Architecture Summary

* **Current Database**: SQLite 3 (local file `forge.db`)
* **Current Driver**: `aiosqlite` (v0.22.1, async I/O)
* **ORM**: SQLAlchemy 2.0.52 (`DeclarativeBase`, `Mapped`, `mapped_column`, `async_sessionmaker`, `create_async_engine`)
* **Migration System**: Lightweight programmatic schema synchronization via `conn.run_sync(Base.metadata.create_all)` with fallback `ALTER TABLE` migrations in `apps/api/app/core/database.py:init_db()`. No Alembic migrations currently configured.
* **Configuration Vector**: `DATABASE_URL` loaded via `python-dotenv` from `.env` or system environment (`apps/api/app/core/config.py`). Default: `sqlite+aiosqlite:///forge.db`.

---

## 2. Models & Entities Inventory

All models inherit from `app.core.database.Base` in `apps/api/app/models/entities.py`:

| Table Name | Primary Key | Foreign Keys | Key Column Types | Postgres Compatibility |
| :--- | :--- | :--- | :--- | :--- |
| `experiments` | `id` (UUID v4 str) | None | `String(64)`, `String(255)`, `Text`, `JSON`, `DateTime(tz)` | **100% Compatible** |
| `generations` | `id` (UUID v4 str) | `experiments.id` | `String(64)`, `Integer`, `JSON`, `Text`, `DateTime(tz)` | **100% Compatible** |
| `executions` | `id` (UUID v4 str) | `experiments.id`, `generations.id` | `String(64)`, `String(128)`, `JSON`, `DateTime(tz)` | **100% Compatible** |
| `trace_events` | `id` (UUID v4 str) | `experiments.id` | `String(64)`, `JSON`, `previous_event_hash`, `event_hash` | **100% Compatible** |
| `mutations` | `id` (UUID v4 str) | None (explicit string FK) | `String(64)`, `String(128)`, `Text`, `JSON`, `DateTime(tz)` | **100% Compatible** |
| `tool_memories` | `id` (UUID v4 str) | `experiments.id` | `String(64)`, `Float`, `Integer`, `Text`, `DateTime(tz)` | **100% Compatible** |

**Total Tables**: 6  
**ORM Cascades**: `cascade="all, delete-orphan"` on `generations`, `events`, `executions`, `memories`. Fully supported by PostgreSQL.

---

## 3. SQLite-Specific Code & Dialect Dependencies

1. **Connection Arguments (`apps/api/app/core/database.py:8`)**:
   ```python
   connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
   ```
   *Analysis*: Already written defensively. When `DATABASE_URL` points to PostgreSQL, `check_same_thread` is automatically omitted.
2. **Dynamic Table Alterations (`apps/api/app/core/database.py:36-49`)**:
   ```python
   migrations = [
       "ALTER TABLE generations ADD COLUMN benchmark_version VARCHAR(32) DEFAULT '2.0.0'",
       "ALTER TABLE generations ADD COLUMN decision_id VARCHAR(64)",
       "ALTER TABLE mutations ADD COLUMN failure_cluster_id VARCHAR(64)",
       "ALTER TABLE mutations ADD COLUMN failure_ids JSON DEFAULT '[]'",
       "ALTER TABLE tool_memories ADD COLUMN execution_id VARCHAR(64)",
       "ALTER TABLE tool_memories ADD COLUMN failure_id VARCHAR(64)",
       "ALTER TABLE tool_memories ADD COLUMN reflection_id VARCHAR(64)",
   ]
   ```
   *Analysis*:
   * On a fresh Supabase database, `Base.metadata.create_all` generates all 6 tables with these columns already declared on the models.
   * However, raw `ALTER TABLE ... ADD COLUMN failure_ids JSON DEFAULT '[]'` in PostgreSQL requires proper type-casting syntax (`DEFAULT '[]'::json` or `::jsonb`) if executed on an existing table. In `init_db()`, this block is wrapped in `try...except Exception: pass`, so it will not crash, but it should be cleaned up.
3. **Raw SQL Audit**:
   * A repository-wide audit found **zero raw SQL queries** in application services (`ExperimentService`, `EvolutionEngine`, `Verifier`, `EventRecorder`, etc.).
   * 100% of data reads and writes use SQLAlchemy 2.0 statements (`select()`, `db.add()`, `db.delete()`, `scalar_one_or_none()`, `scalars().all()`).
4. **Data Types**:
   * `JSON`: Handled natively by PostgreSQL (`json` or `jsonb`).
   * `DateTime(timezone=True)`: Maps to PostgreSQL `TIMESTAMP WITH TIME ZONE`.
   * UUID strings (`String(64)`): Compatible with standard `VARCHAR(64)` in PostgreSQL.

---

## 4. Postgres Compatibility Assessment

* **ORM Layer**: SQLAlchemy 2.0 has first-class, battle-tested PostgreSQL dialect support.
* **Driver Selection**: `asyncpg` is the gold standard for high-performance asynchronous PostgreSQL with SQLAlchemy.
* **Connection String Format**:
  * Direct connection: `postgresql+asyncpg://postgres:[PASSWORD]@[HOST]:5432/postgres`
  * Supabase Transaction Pooler (PgBouncer / Supavisor): `postgresql+asyncpg://postgres.[REF]:[PASSWORD]@[POOLER_HOST]:6543/postgres`
* **JSON Serialization**: `asyncpg` natively serializes Python `dict` and `list` into PostgreSQL JSON columns without requiring custom encoders.

---

## 5. Required Changes for Supabase Deployment

1. **Add PostgreSQL Driver**:
   * Add `asyncpg>=0.29.0` to `apps/api/requirements.txt`.
2. **Connection Engine Configuration (`apps/api/app/core/database.py`)**:
   * Add pooling parameters suitable for cloud deployment:
     ```python
     if "postgresql" in settings.database_url:
         engine_kwargs = {
             "pool_size": 10,
             "max_overflow": 20,
             "pool_pre_ping": True,
             # When using Supabase transaction pooler (port 6543):
             # "connect_args": {"statement_cache_size": 0}
         }
     ```
3. **Environment Configuration**:
   * In local development, maintain:
     ```env
     DATABASE_URL=sqlite+aiosqlite:///forge.db
     ```
   * In production (e.g. Render / Railway / Fly.io / Modal / AWS):
     ```env
     DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@[HOST]:5432/postgres
     ```
4. **CORS & Public API Access**:
   * Verify CORS settings in `apps/api/app/main.py` allow the deployed Vercel domain (`https://forge-*.vercel.app`).

---

## 6. Potential Risks & Mitigations

| Risk | Severity | Mitigation |
| :--- | :--- | :--- |
| **Connection Exhaustion on Supabase** | Medium | Use Supabase's built-in connection pooler (port 6543) or configure `pool_size=5`, `max_overflow=10`, `pool_pre_ping=True` in SQLAlchemy. |
| **`asyncpg` Prepared Statement Conflict with PgBouncer** | Medium | If connecting via transaction pooler (port 6543), pass `statement_cache_size=0` in `connect_args` to prevent prepared statement collisions. |
| **Cold Starts & Network Latency** | Low | Locate the FastAPI backend in the same cloud region as the Supabase project (e.g., `aws-us-east-1` or `aws-eu-west-1`). |
| **Database Credentials Exposure** | High | Keep `DATABASE_URL` strictly in backend environment variables. Frontend (Next.js) must only communicate with FastAPI endpoints (`/api/...`). |
| **Local Test Divergence** | Low | Pytest suite can continue using `sqlite+aiosqlite` for sub-second execution speed, or use a Dockerized PostgreSQL instance in CI. |

---

## 7. Recommended Migration Path

1. **Phase 1 (Audit)**: Completed (this document).
2. **Phase 2 (Dependency Addition)**: Add `asyncpg` to `apps/api/requirements.txt`.
3. **Phase 3 (Engine Hardening)**: Update `apps/api/app/core/database.py` to support `pool_pre_ping` and `statement_cache_size=0` when connecting to PostgreSQL.
4. **Phase 4 (Supabase Project Provisioning)**:
   * Create Supabase project.
   * Copy the connection URI string.
   * Prepend `postgresql+asyncpg://`.
5. **Phase 5 (Verification)**: Run `init_db()` against Supabase. Verify all 6 tables are created with proper indexes and constraints.
6. **Phase 6 (Deployment)**:
   * Deploy FastAPI backend (Render / Railway / Fly.io).
   * Deploy Next.js frontend (Vercel) pointing `NEXT_PUBLIC_API_URL` to FastAPI backend.

---

## 8. Status Determination

**DEPLOYMENT-A STATUS: READY**  
The database layer is clean, modern SQLAlchemy 2.0 with zero raw database dependencies. Moving to Supabase Postgres requires only adding `asyncpg` and configuring the connection string.
