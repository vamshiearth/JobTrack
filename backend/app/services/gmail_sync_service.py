from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import EmailMessage, GmailConnection, GmailSyncState
from app.services.gmail_history_planning import parse_history_page
from app.services.gmail_metadata_client import GmailAPIError, GmailHistoryExpired, GmailMetadataClient, GmailMessageMetadata
from app.services.gmail_token_crypto import GmailTokenCryptoError, get_gmail_token_crypto
from app.services.gmail_token_refresh import GmailTokenRefreshError, refresh_gmail_access_token


class GmailSyncError(Exception):
    pass


class GmailSyncNotEligible(GmailSyncError):
    pass


class GmailSyncBusy(GmailSyncError):
    pass


class GmailSyncUnavailable(GmailSyncError):
    pass


@dataclass(frozen=True)
class GmailSyncResult:
    mode: str
    messages_fetched: int
    messages_updated: int
    messages_deleted: int
    completed: bool


def _lock_key(connection_id: UUID) -> int:
    return int.from_bytes(connection_id.bytes[:8], "big", signed=True)


def _upsert_message(db: Session, connection_id: UUID, metadata: GmailMessageMetadata) -> bool:
    message = db.scalar(select(EmailMessage).where(EmailMessage.gmail_connection_id == connection_id, EmailMessage.gmail_message_id == metadata.message_id).with_for_update())
    received_at = datetime.fromtimestamp((metadata.internal_date_ms or 0) / 1000, tz=timezone.utc)
    headers = metadata.headers
    if message is None:
        db.add(EmailMessage(gmail_connection_id=connection_id, gmail_message_id=metadata.message_id, gmail_thread_id=metadata.thread_id, sender_address=headers.get("from"), subject=headers.get("subject"), received_at=received_at, classification_kind="UNCLASSIFIED", processing_status="PENDING"))
        return True
    message.gmail_thread_id = metadata.thread_id
    message.sender_address = headers.get("from")
    message.subject = headers.get("subject")
    message.received_at = received_at
    return False


def _import_baseline(db: Session, client: GmailMetadataClient, connection_id: UUID, limit: int, baseline_cursor: str) -> tuple[int, int]:
    ids: list[str] = []
    token: str | None = None
    while len(ids) < limit:
        payload = client.list_messages(page_token=token, max_results=min(100, limit - len(ids)))
        for item in payload.get("messages", []):
            if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"] not in ids:
                ids.append(item["id"])
                if len(ids) == limit:
                    break
        token = payload.get("nextPageToken") if isinstance(payload.get("nextPageToken"), str) else None
        if not token:
            break
    updated = sum(_upsert_message(db, connection_id, client.get_message(message_id)) for message_id in ids)
    return len(ids), updated


def _incremental(db: Session, client: GmailMetadataClient, connection_id: UUID, cursor: str) -> tuple[int, int, int, str]:
    refresh: list[str] = []
    deleted: set[str] = set()
    token: str | None = None
    final_cursor: str | None = None
    while True:
        changes = parse_history_page(client.history(cursor, page_token=token))
        refresh.extend(sorted(changes.refresh_ids - deleted))
        deleted.update(changes.deleted_ids)
        refresh = [message_id for message_id in refresh if message_id not in deleted]
        final_cursor = changes.response_history_id or final_cursor
        token = changes.next_page_token
        if not token:
            break
    deleted_count = db.execute(delete(EmailMessage).where(EmailMessage.gmail_connection_id == connection_id, EmailMessage.gmail_message_id.in_(deleted), EmailMessage.job_application_id.is_(None))).rowcount or 0
    fetched = 0
    updated = 0
    for message_id in dict.fromkeys(refresh):
        updated += int(_upsert_message(db, connection_id, client.get_message(message_id)))
        fetched += 1
    if not final_cursor:
        raise GmailSyncUnavailable("Gmail did not provide a history cursor")
    return fetched, updated, deleted_count, final_cursor


def sync_gmail_connection(db: Session, *, user_id: UUID, connection_id: UUID) -> GmailSyncResult:
    settings = get_settings()
    connection = db.scalar(select(GmailConnection).where(GmailConnection.id == connection_id, GmailConnection.user_id == user_id).with_for_update())
    if connection is None or connection.connection_status != "CONNECTED" or GmailMetadataScope not in connection.granted_scopes:
        raise GmailSyncNotEligible("Gmail connection is not eligible for synchronization")
    lock_acquired = db.scalar(select(text("pg_try_advisory_xact_lock(:lock_key)")).params(lock_key=_lock_key(connection_id)))
    if not lock_acquired:
        raise GmailSyncBusy("Gmail synchronization is already running")
    if not connection.encrypted_refresh_token:
        raise GmailSyncNotEligible("Gmail connection has no credential")
    try:
        access_token = refresh_gmail_access_token(client_id=settings.gmail_oauth_client_id or "", client_secret=settings.gmail_oauth_client_secret or "", refresh_token=get_gmail_token_crypto().decrypt(connection.encrypted_refresh_token))
        client = GmailMetadataClient(access_token)
        try:
            state = db.scalar(select(GmailSyncState).where(GmailSyncState.gmail_connection_id == connection.id).with_for_update())
            if state is None:
                state = GmailSyncState(gmail_connection_id=connection.id, sync_status="RUNNING")
                db.add(state)
                db.flush()
            state.sync_status = "RUNNING"
            state.last_attempt_at = datetime.now(timezone.utc)
            profile = client.profile()
            baseline = profile.get("historyId") if isinstance(profile.get("historyId"), str) else None
            if not baseline:
                raise GmailSyncUnavailable("Gmail did not provide a history cursor")
            if state.last_history_id is None:
                fetched, updated = _import_baseline(db, client, connection.id, settings.gmail_initial_sync_limit, baseline)
                mode = "INITIAL"
                deleted = 0
                cursor = baseline
            else:
                try:
                    fetched, updated, deleted, cursor = _incremental(db, client, connection.id, state.last_history_id)
                    mode = "INCREMENTAL"
                except GmailHistoryExpired:
                    fetched, updated = _import_baseline(db, client, connection.id, settings.gmail_initial_sync_limit, baseline)
                    mode = "BASELINE_RESTART"
                    deleted = 0
                    cursor = baseline
            connection_check = db.scalar(select(GmailConnection.connection_status).where(GmailConnection.id == connection.id, GmailConnection.user_id == user_id))
            if connection_check != "CONNECTED":
                raise GmailSyncNotEligible("Gmail connection changed during synchronization")
            state.last_history_id = cursor
            state.sync_status = "IDLE"
            state.last_successful_sync_at = datetime.now(timezone.utc)
            state.last_error_message = None
            db.commit()
            return GmailSyncResult(mode, fetched, updated, deleted, True)
        finally:
            client.close()
    except (GmailTokenCryptoError, GmailTokenRefreshError) as exc:
        db.rollback()
        connection = db.scalar(select(GmailConnection).where(GmailConnection.id == connection_id, GmailConnection.user_id == user_id))
        if connection is not None and connection.connection_status == "CONNECTED":
            connection.connection_status = "RECONNECT_REQUIRED"
            db.commit()
        else:
            db.rollback()
        raise GmailSyncNotEligible("Gmail requires reconnection") from exc
    except (GmailAPIError, GmailSyncError):
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise GmailSyncUnavailable("Gmail synchronization failed") from exc


GmailMetadataScope = "https://www.googleapis.com/auth/gmail.metadata"
