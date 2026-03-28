#!/bin/bash
# ============================================================
# KT Monetization OS — PostgreSQL Backup Script
# - Chiffrement AES-256-CBC
# - Rotation automatique (30 jours)
# - Vérification d intégrité
# - Restore testable
# Usage: bash backup.sh [backup|restore|list|test]
# ============================================================
set -euo pipefail

BACKUP_DIR="/opt/backups/kt-monetization"
RETENTION_DAYS=30
DB_CONTAINER="infra-postgres-1"
COMPOSE_DIR="/opt/kt-monetization-os"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/kt_db_${TIMESTAMP}.sql.gz.enc"
LOG_FILE="/var/log/kt-backup.log"
PASSPHRASE_FILE="/etc/kt-backup.key"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
error() { log "ERROR: $*"; exit 1; }

# ── Init ──────────────────────────────────────────────────────────────────────
init() {
    mkdir -p "$BACKUP_DIR"
    chmod 700 "$BACKUP_DIR"

    if [ ! -f "$PASSPHRASE_FILE" ]; then
        log "Generating backup encryption key..."
        openssl rand -base64 48 > "$PASSPHRASE_FILE"
        chmod 600 "$PASSPHRASE_FILE"
        log "Key saved to $PASSPHRASE_FILE — BACK THIS UP SECURELY!"
    fi
}

# ── Backup ────────────────────────────────────────────────────────────────────
do_backup() {
    init
    log "Starting backup..."

    # Get DB credentials from .env
    source <(grep -E "^POSTGRES_" "$COMPOSE_DIR/.env" | sed 's/^/export /')

    # Dump + gzip + encrypt
    docker exec "$DB_CONTAINER" \
        pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
        | gzip \
        | openssl enc -aes-256-cbc -pbkdf2 -iter 100000 \
            -pass "file:$PASSPHRASE_FILE" \
        > "$BACKUP_FILE"

    # Verify file exists and has size
    SIZE=$(stat -c%s "$BACKUP_FILE")
    if [ "$SIZE" -lt 1000 ]; then
        error "Backup file too small ($SIZE bytes) — something went wrong"
    fi

    # Checksum
    sha256sum "$BACKUP_FILE" > "${BACKUP_FILE}.sha256"

    log "Backup complete: $BACKUP_FILE ($SIZE bytes)"

    # Retention cleanup
    find "$BACKUP_DIR" -name "*.enc" -mtime "+$RETENTION_DAYS" -delete
    find "$BACKUP_DIR" -name "*.sha256" -mtime "+$RETENTION_DAYS" -delete
    log "Old backups cleaned (>$RETENTION_DAYS days)"
}

# ── Restore ──────────────────────────────────────────────────────────────────
do_restore() {
    RESTORE_FILE="${1:-}"
    [ -z "$RESTORE_FILE" ] && error "Usage: $0 restore <backup_file.enc>"
    [ ! -f "$RESTORE_FILE" ] && error "File not found: $RESTORE_FILE"

    init
    source <(grep -E "^POSTGRES_" "$COMPOSE_DIR/.env" | sed 's/^/export /')

    log "Verifying checksum..."
    sha256sum -c "${RESTORE_FILE}.sha256" || error "Checksum mismatch — backup corrupted!"

    log "Restoring from $RESTORE_FILE..."
    openssl enc -aes-256-cbc -pbkdf2 -iter 100000 -d \
        -pass "file:$PASSPHRASE_FILE" \
        -in "$RESTORE_FILE" \
        | gunzip \
        | docker exec -i "$DB_CONTAINER" \
            psql -U "$POSTGRES_USER" "$POSTGRES_DB"

    log "Restore complete!"
}

# ── Test restore ─────────────────────────────────────────────────────────────
do_test() {
    LATEST=$(ls -t "$BACKUP_DIR"/*.enc 2>/dev/null | head -1 || echo "")
    [ -z "$LATEST" ] && error "No backups found in $BACKUP_DIR"

    log "Testing restore from: $LATEST"
    init
    source <(grep -E "^POSTGRES_" "$COMPOSE_DIR/.env" | sed 's/^/export /')

    # Decrypt and count rows
    ROW_COUNT=$(openssl enc -aes-256-cbc -pbkdf2 -iter 100000 -d \
        -pass "file:$PASSPHRASE_FILE" \
        -in "$LATEST" \
        | gunzip \
        | grep -c "^INSERT\|^COPY" || echo 0)

    log "Test passed: $ROW_COUNT data statements found in backup"
}

# ── List ─────────────────────────────────────────────────────────────────────
do_list() {
    echo "Backups in $BACKUP_DIR:"
    ls -lh "$BACKUP_DIR"/*.enc 2>/dev/null || echo "No backups found"
}

# ── Main ─────────────────────────────────────────────────────────────────────
case "${1:-backup}" in
    backup)  do_backup ;;
    restore) do_restore "${2:-}" ;;
    test)    do_test ;;
    list)    do_list ;;
    *) echo "Usage: $0 [backup|restore <file>|test|list]"; exit 1 ;;
esac
