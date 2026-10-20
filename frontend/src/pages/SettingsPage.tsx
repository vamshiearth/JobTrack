import { useEffect, useState } from 'react'
import {
  disconnectGmail,
  getGmailConnection,
  getGmailSyncStatus,
  startGmailConnection,
  triggerGmailSync,
  type GmailConnection,
  type GmailSyncStatus,
} from '../api/gmail'
import { useSession } from '../auth/useSession'

export default function SettingsPage() {
  const session = useSession()
  const [connection, setConnection] = useState<GmailConnection | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [syncStatus, setSyncStatus] = useState<GmailSyncStatus | null>(null)

  useEffect(() => {
    void getGmailConnection()
      .then(setConnection)
      .catch((reason: unknown) =>
        setError(
          reason instanceof Error
            ? reason.message
            : 'Unable to load Gmail status',
        ),
      )
    void getGmailSyncStatus()
      .then(setSyncStatus)
      .catch(() => undefined)
  }, [])

  async function connect() {
    setBusy(true)
    setError(null)
    try {
      const result = await startGmailConnection(session.user!.csrf_token)
      window.location.assign(result.authorization_url)
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : 'Unable to connect Gmail',
      )
      setBusy(false)
    }
  }

  async function disconnect() {
    setBusy(true)
    setError(null)
    try {
      await disconnectGmail(session.user!.csrf_token)
      setConnection({
        connected: false,
        email: null,
        status: 'DISCONNECTED',
        granted_scopes: [],
        last_synced_at: null,
      })
      setSyncStatus(null)
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : 'Unable to disconnect Gmail',
      )
    } finally {
      setBusy(false)
    }
  }

  async function sync() {
    setBusy(true)
    setError(null)
    try {
      await triggerGmailSync(session.user!.csrf_token)
      setSyncStatus(await getGmailSyncStatus())
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : 'Unable to sync Gmail',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className='page-section'>
      <h2>Settings</h2>
      <div className='settings-panel'>
        <h3>Gmail connection</h3>
        <p>
          {connection?.connected
            ? `Connected as ${connection.email}`
            : 'Connect Gmail to prepare for mailbox-aware features.'}
        </p>
        {error && <p role='alert'>{error}</p>}
        {connection?.connected ? (
          <>
            <button
              type='button'
              onClick={() => void sync()}
              disabled={busy || syncStatus?.requires_reconnection}
            >
              Sync Gmail now
            </button>
            <button
              type='button'
              onClick={() => void disconnect()}
              disabled={busy}
            >
              Disconnect Gmail
            </button>
            {syncStatus && (
              <p>
                {syncStatus.last_sync_status} · {syncStatus.message_count}{' '}
                metadata records
              </p>
            )}
            {syncStatus?.requires_reconnection && (
              <p role='alert'>Gmail requires reconnection.</p>
            )}
          </>
        ) : (
          <button
            type='button'
            onClick={() => void connect()}
            disabled={busy || !connection}
          >
            Connect Gmail
          </button>
        )}
      </div>
    </section>
  )
}
