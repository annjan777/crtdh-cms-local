import { useEffect, useState } from 'react';
import { Mail } from 'lucide-react';
import apiClient from '../api/client';
import ConfirmDialog from '../components/ConfirmDialog';
import EmptyState from '../components/EmptyState';
import Spinner from '../components/Spinner';
import { useToast } from '../context/ToastContext';

export default function ContactMessagesPage() {
  const toast = useToast();
  const [messages, setMessages] = useState(null);
  const [error, setError] = useState('');
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  function load() {
    apiClient
      .get('/contact-messages/')
      .then(({ data }) => setMessages(Array.isArray(data) ? data : data.results))
      .catch(() => setError('Could not load contact messages.'));
  }

  useEffect(load, []);

  async function confirmDelete() {
    setDeleting(true);
    try {
      await apiClient.delete(`/contact-messages/${pendingDelete.id}/`);
      setMessages((prev) => prev.filter((m) => m.id !== pendingDelete.id));
      setPendingDelete(null);
      toast.success('Message deleted.');
    } catch {
      setError('Could not delete message.');
      toast.error('Could not delete message.');
    } finally {
      setDeleting(false);
    }
  }

  if (error) return <div className="form-error">{error}</div>;
  if (messages === null) return <Spinner label="Loading contact messages…" />;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>
            <Mail size={20} className="page-title-icon" aria-hidden="true" />
            Contact Messages
          </h1>
          <p className="page-lead">Read-only submissions from the public contact form. Staff can delete entries.</p>
        </div>
      </div>

      {messages.length === 0 ? (
        <EmptyState icon={Mail} title="No messages yet" description="Submissions from the public contact form will show up here." />
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Message</th>
              <th>Received</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {messages.map((m) => (
              <tr key={m.id}>
                <td>{m.name}</td>
                <td>{m.email}</td>
                <td>{m.phone}</td>
                <td className="cell-truncate">{m.message}</td>
                <td>{m.created_at ? new Date(m.created_at).toLocaleString() : ''}</td>
                <td>
                  <button type="button" className="btn btn-danger btn-small" onClick={() => setPendingDelete(m)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <ConfirmDialog
        open={!!pendingDelete}
        title="Delete message"
        message={`Delete the message from "${pendingDelete?.name}"? This cannot be undone.`}
        onCancel={() => setPendingDelete(null)}
        onConfirm={confirmDelete}
        busy={deleting}
      />
    </div>
  );
}
