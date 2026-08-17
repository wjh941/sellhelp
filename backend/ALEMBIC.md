# SQLite Alembic Migration Guide

## Safety rule

Back up the SQLite database file before running any Alembic command that targets it. Stop the backend first so the backup is consistent. Do not run `alembic downgrade` for the initial schema revision: it is intentionally blocked to prevent table and data deletion.

For the default database, create a timestamped copy before proceeding:

```powershell
Copy-Item -LiteralPath .\yingtai.db -Destination .\backup\yingtai-before-alembic-YYYYMMDD-HHMMSS.db
```

Alembic reads `SELLHELP_DATABASE_URL`, the same connection string used by the application. A command-line URL can be supplied only for an explicit disposable database with `-x database_url=...`.

Run the commands below from the `backend` directory.

## Initial migration

`alembic/versions/d8f13722a89d_initial_schema.py` is the initial baseline generated from `app.models.all_models.Base.metadata`.

1. Its `upgrade()` creates the current tables, foreign keys, and indexes for an empty database. It does not insert seed data, alter existing rows, or drop anything.
2. Its `downgrade()` raises an error before the generated removal operations so this revision cannot be used to delete an application schema.
3. Alembic records the applied revision in its own `alembic_version` table. That metadata table is the only table touched by `stamp`.

## Existing populated database

Use these steps for the existing `yingtai.db` or any populated operator database. Do not run `upgrade head`: the tables already exist and Alembic would attempt to create them again.

1. Stop the backend process.
2. Back up the exact SQLite file with the command above.
3. Point the environment variable at that file when it is not the default database:

```powershell
$env:SELLHELP_DATABASE_URL = "sqlite:///C:/data/sellhelp.db"
```

4. Mark the already-present Phase 1 schema as the initial revision without executing schema DDL:

```powershell
python -m alembic stamp d8f13722a89d
```

5. Apply the additive Phase 2 revision:

```powershell
python -m alembic upgrade head
```

6. Confirm the recorded revision:

```powershell
python -m alembic current
```

`stamp d8f13722a89d` preserves the existing business tables and rows. It only creates or updates Alembic's revision marker. `upgrade head` then creates only the new access-control tables and inserts the built-in role/configuration rows; it does not drop or alter existing business tables.

## Phase 2 access control migration

`alembic/versions/35e9adbe883f_add_auth_and_audit_tables.py` is an additive, forward-only migration.

1. **Before applying this migration, stop the backend and back up the exact SQLite database file.** Do not skip the backup even though this migration has no drop-table or drop-column statements.
2. The migration creates `roles`, `users`, `user_roles`, and `audit_logs`, with their required indexes and foreign keys.
3. It inserts the built-in `owner`, `warehouse_operator`, and `sales_clerk` roles.
4. It inserts `system_configs.standalone_mode = true` only when that config entry does not already exist. Legacy single-machine usage continues without a login until an owner deliberately disables standalone mode.
5. Its `downgrade()` always raises an error; access records and audit data must not be removed through Alembic downgrade.

When turning off standalone mode, set a separate 32-character-or-longer JWT secret before restarting the backend:

```powershell
$env:SELLHELP_JWT_SECRET = "replace-with-a-private-random-secret-of-at-least-32-characters"
```

After the migration, use standalone mode once to create the first owner account. Set `standalone_mode` to `false` only after that account and the JWT secret are in place.

## New empty database

Use these steps only for a new empty SQLite database.

1. Set `SELLHELP_DATABASE_URL` if the database is not the default path.
2. Create the schema with the non-destructive forward migration:

```powershell
python -m alembic upgrade head
```

3. Verify the revision:

```powershell
python -m alembic current
```

4. Run `python -m app.init_data` only when default sample categories, supplier, and customers are wanted.

## Disposable verification

The following command is safe for migration validation because it targets a newly created temporary file, never `yingtai.db`:

```powershell
python -m alembic -x database_url=sqlite:///C:/Temp/sellhelp-migration-check.db upgrade head
```
