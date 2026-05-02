# Backup and Restore Runbook

**Last updated:** 2026-05-01
**Applies to:** AI Workflow Control Plane v3.0+

---

## Overview

This runbook covers backup and restore procedures for the PostgreSQL database that stores all platform state: runs, traces, tool calls, approvals, workflows, evals, audit logs, users, and connector configurations.

---

## 1. Routine Backup

### pg_dump (full logical backup)

```bash
# Backup with timestamp
pg_dump -h localhost -U postgres -d ai_workflow \
  --format=custom \
  --compress=9 \
  --file=backup_$(date +%Y%m%d_%H%M%S).dump

# With Docker
docker exec postgres pg_dump -U postgres -d ai_workflow \
  --format=custom --compress=9 > backup_$(date +%Y%m%d_%H%M%S).dump
```

### Backup schedule recommendation

| Frequency | Retention | Command |
|-----------|-----------|---------|
| Daily | 7 days | Cron job at 03:00 UTC |
| Weekly | 30 days | Sunday 04:00 UTC |
| Pre-migration | Until verified | Manual before `alembic upgrade` |

### Automate with cron

```bash
# /etc/cron.d/ai-workflow-backup
0 3 * * * postgres pg_dump -h localhost -U postgres -d ai_workflow --format=custom --compress=9 --file=/backups/ai_workflow_$(date +\%Y\%m\%d).dump
```

---

## 2. Restore

### From pg_dump backup

```bash
# Stop the application first
./stop.sh

# Drop and recreate the database
dropdb -h localhost -U postgres ai_workflow
createdb -h localhost -U postgres ai_workflow

# Restore
pg_restore -h localhost -U postgres -d ai_workflow --no-owner backup_20260501.dump

# Verify
psql -h localhost -U postgres -d ai_workflow -c "SELECT count(*) FROM runs;"

# Restart
./start.sh
```

### With Docker

```bash
docker stop ai-workflow-backend
docker exec -i postgres dropdb -U postgres ai_workflow
docker exec -i postgres createdb -U postgres ai_workflow
docker exec -i postgres pg_restore -U postgres -d ai_workflow --no-owner < backup.dump
docker start ai-workflow-backend
```

---

## 3. Migration Backup

**Always back up before running migrations.**

```bash
# 1. Backup
pg_dump -h localhost -U postgres -d ai_workflow \
  --format=custom --file=pre_migration_backup.dump

# 2. Run migration
cd backend && alembic upgrade head

# 3. Smoke test (see section 4)

# 4. If migration fails, restore:
# pg_restore -h localhost -U postgres -d ai_workflow --no-owner pre_migration_backup.dump
```

---

## 4. Post-Migration Smoke Test

After any migration or restore, verify these:

```bash
# API health
curl -s http://localhost:8000/health | jq .

# Database version
curl -s http://localhost:8000/health | jq '.database.migration_version'

# Core tables exist and are queryable
psql -h localhost -U postgres -d ai_workflow -c "\dt"

# Key counts (should not be zero if data existed before)
psql -h localhost -U postgres -d ai_workflow -c "
  SELECT 'runs' as t, count(*) FROM runs
  UNION ALL SELECT 'trace_spans', count(*) FROM trace_spans
  UNION ALL SELECT 'approvals', count(*) FROM approvals
  UNION ALL SELECT 'users', count(*) FROM users;
"

# Workers can connect
curl -s http://localhost:8000/api/metrics | jq '.workers'
```

---

## 5. Rollback Strategy

### Alembic rollback

```bash
# Rollback one migration
cd backend && alembic downgrade -1

# Rollback to specific version
cd backend && alembic downgrade <version_id>

# Rollback to empty (destructive)
cd backend && alembic downgrade base
```

### Full rollback from backup

If Alembic rollback is not possible:

1. Stop all workers and the API
2. Drop the database
3. Restore from pre-migration backup
4. Downgrade the Alembic version in the database:
   ```sql
   UPDATE alembic_version SET version_num = '<previous_version>';
   ```
5. Restart with the previous code version

---

## 6. ENCRYPTION_KEY Considerations

**Critical:** Connector secrets are encrypted with `ENCRYPTION_KEY`. If you lose this key, all encrypted secrets become unreadable.

### Backup the key

```bash
# Include in your backup script
echo "$ENCRYPTION_KEY" > /secure/encryption_key_backup.txt
chmod 600 /secure/encryption_key_backup.txt
```

### Key rotation

If you need to rotate the key:

1. Read all connector configs with the old key
2. Decrypt secrets
3. Set new `ENCRYPTION_KEY`
4. Re-encrypt secrets with the new key
5. Update the database

```python
# Key rotation script (run in backend/)
from security.secret_manager import decrypt_config_secrets, encrypt_config_secrets
from database import SessionLocal
from models import ConnectorConfig
import os

old_key = "old-key"
new_key = "new-key"

db = SessionLocal()
for connector in db.query(ConnectorConfig).all():
    if connector.config_json:
        os.environ["ENCRYPTION_KEY"] = old_key
        from security import secret_manager
        secret_manager._fernet = None  # reset cache
        decrypted = decrypt_config_secrets(connector.config_json)

        os.environ["ENCRYPTION_KEY"] = new_key
        secret_manager._fernet = None
        connector.config_json = encrypt_config_secrets(decrypted)

db.commit()
```

### Risk: connector secret dependency

- If `ENCRYPTION_KEY` is lost, connector configs with secrets (API keys, webhook secrets) **cannot be recovered** from the database
- The secrets must be re-entered manually
- **Always back up the encryption key separately from the database backup**

---

## 7. Backup Verification

Periodically verify backups are restorable:

```bash
# Restore to a test database
createdb -h localhost -U postgres ai_workflow_test
pg_restore -h localhost -U postgres -d ai_workflow_test --no-owner backup.dump

# Verify counts match
psql -h localhost -U postgres -d ai_workflow_test -c "SELECT count(*) FROM runs;"
psql -h localhost -U postgres -d ai_workflow -c "SELECT count(*) FROM runs;"

# Cleanup
dropdb -h localhost -U postgres ai_workflow_test
```

---

## 8. Disaster Recovery Checklist

- [ ] Database backup exists (check `/backups/` or S3)
- [ ] `ENCRYPTION_KEY` is backed up separately
- [ ] `JWT_SECRET` is documented (can be regenerated, but existing tokens will expire)
- [ ] `SERVICE_TOKENS` are documented
- [ ] Alembic migration history is in version control
- [ ] Test restore to a clean database succeeds
- [ ] Smoke test passes after restore
- [ ] Workers reconnect after restore
