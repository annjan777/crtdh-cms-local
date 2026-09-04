import { useEffect, useState } from 'react';
import { Link2, Plus, X } from 'lucide-react';
import apiClient from '../api/client';
import { useToast } from '../context/ToastContext';

export default function NavbarMenuLinksManager() {
  const { addToast } = useToast();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [draggedId, setDraggedId] = useState(null);
  const [dragOverBucket, setDragOverBucket] = useState(null);

  // Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [formData, setFormData] = useState({ label: '', url: '', in_more: false });

  const fetchItems = async () => {
    try {
      setLoading(true);
      const res = await apiClient.get('/nav-items/');
      const data = Array.isArray(res.data) ? res.data : res.data.results || [];
      const sorted = [...data].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
      setItems(sorted);
    } catch (err) {
      console.error('Failed to load nav items', err);
      addToast('Failed to load navigation items.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, []);

  const mainNavItems = items.filter((item) => !item.in_more);
  const moreNavItems = items.filter((item) => item.in_more);

  // Re-index orders sequentially and save to API
  const persistChanges = async (updatedItems) => {
    const indexed = updatedItems.map((item, idx) => ({
      ...item,
      order: idx,
    }));

    setItems(indexed);

    try {
      await Promise.all(
        indexed.map((item) =>
          apiClient.patch(`/nav-items/${item.id}/`, {
            label: item.label,
            url: item.url,
            order: item.order,
            in_more: item.in_more,
          })
        )
      );
      addToast('Navbar layout saved.', 'success');
    } catch (err) {
      console.error('Failed to save layout', err);
      addToast('Failed to update navbar layout.', 'error');
      fetchItems();
    }
  };

  // Toggle bucket for an item (1-click move)
  const handleToggleBucket = (id, targetInMore) => {
    const targetItem = items.find((i) => i.id === id);
    if (!targetItem) return;

    const remaining = items.filter((i) => i.id !== id);
    const updatedItem = { ...targetItem, in_more: targetInMore };

    let updated;
    if (!targetInMore) {
      const mainItems = remaining.filter((i) => !i.in_more);
      const moreItems = remaining.filter((i) => i.in_more);
      updated = [...mainItems, updatedItem, ...moreItems];
    } else {
      updated = [...remaining, updatedItem];
    }

    persistChanges(updated);
  };

  // HTML5 Drag & Drop Handlers
  const handleDragStart = (e, id) => {
    setDraggedId(id);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', id.toString());
  };

  const handleDragOverContainer = (e, bucketName) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (dragOverBucket !== bucketName) {
      setDragOverBucket(bucketName);
    }
  };

  const handleDragLeaveContainer = () => {
    setDragOverBucket(null);
  };

  const handleDropOnBucket = (e, targetInMore) => {
    e.preventDefault();
    setDragOverBucket(null);

    const id = draggedId || parseInt(e.dataTransfer.getData('text/plain'), 10);
    if (!id) return;

    const draggedItem = items.find((i) => i.id === id);
    if (!draggedItem) return;

    if (draggedItem.in_more !== targetInMore) {
      handleToggleBucket(id, targetInMore);
    }
    setDraggedId(null);
  };

  const handleDropOnCard = (e, targetId, targetInMore) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOverBucket(null);

    const id = draggedId || parseInt(e.dataTransfer.getData('text/plain'), 10);
    if (!id || id === targetId) return;

    const draggedItem = items.find((i) => i.id === id);
    if (!draggedItem) return;

    const updatedDragged = { ...draggedItem, in_more: targetInMore };
    const remaining = items.filter((i) => i.id !== id);
    const targetIdx = remaining.findIndex((i) => i.id === targetId);

    if (targetIdx === -1) return;

    const updated = [...remaining];
    updated.splice(targetIdx, 0, updatedDragged);

    persistChanges(updated);
    setDraggedId(null);
  };

  // Modal Handlers
  const handleOpenAddModal = (defaultInMore = false) => {
    setEditingItem(null);
    setFormData({ label: '', url: '', in_more: defaultInMore });
    setModalOpen(true);
  };

  const handleOpenEditModal = (item) => {
    setEditingItem(item);
    setFormData({ label: item.label, url: item.url, in_more: item.in_more });
    setModalOpen(true);
  };

  const handleSaveModal = async (e) => {
    e.preventDefault();
    if (!formData.label.trim() || !formData.url.trim()) {
      addToast('Please enter both label and URL.', 'error');
      return;
    }

    try {
      if (editingItem) {
        await apiClient.patch(`/nav-items/${editingItem.id}/`, formData);
        addToast('Nav link updated!', 'success');
      } else {
        await apiClient.post('/nav-items/', {
          ...formData,
          order: items.length,
        });
        addToast('New nav link added!', 'success');
      }
      setModalOpen(false);
      fetchItems();
    } catch (err) {
      console.error('Failed to save nav link', err);
      addToast('Error saving nav item.', 'error');
    }
  };

  const handleDeleteItem = async (id, label) => {
    if (!window.confirm(`Are you sure you want to delete "${label}"?`)) return;
    try {
      await apiClient.delete(`/nav-items/${id}/`);
      addToast(`Deleted "${label}"`, 'success');
      fetchItems();
    } catch (err) {
      console.error('Failed to delete nav item', err);
      addToast('Failed to delete nav item.', 'error');
    }
  };

  if (loading && items.length === 0) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
        Loading Nav Items...
      </div>
    );
  }

  return (
    <div>
      {/* Page Header - Matches original admin UI */}
      <div className="page-header">
        <div>
          <h1>
            <Link2 size={20} className="page-title-icon" aria-hidden="true" />
            Nav Items
          </h1>
          <p className="page-lead">
            Drag rows by the handle to reorder. Items under <strong>Nav Bar Items</strong> appear on the top header; items under <strong>More</strong> appear inside the dropdown.
          </p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => handleOpenAddModal(false)}>
          <Plus size={16} aria-hidden="true" />
          Add Nav Item
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
        {/* ================= CONTAINER 1: MAIN NAVBAR ITEMS ================= */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <h2 style={{ fontSize: '13px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>Nav Bar Links</span>
              <span style={{ background: '#e0e7ff', color: '#3730a3', padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: '700' }}>
                {mainNavItems.length}
              </span>
            </h2>
          </div>

          <div
            style={{
              background: dragOverBucket === 'main' ? 'rgba(79, 70, 229, 0.04)' : 'var(--surface)',
              border: dragOverBucket === 'main' ? '2px dashed var(--primary)' : '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              overflow: 'hidden',
              boxShadow: 'var(--shadow-xs)',
              transition: 'all 0.15s ease',
            }}
            onDragOver={(e) => handleDragOverContainer(e, 'main')}
            onDragLeave={handleDragLeaveContainer}
            onDrop={(e) => handleDropOnBucket(e, false)}
          >
            <div
              className="row-grid row-grid-head"
              style={{ gridTemplateColumns: '1fr 1.5fr auto', background: 'var(--surface-hover)', borderBottom: '1px solid var(--border)' }}
            >
              <div className="row-cell">LABEL</div>
              <div className="row-cell">URL</div>
              <div className="row-cell" style={{ textAlign: 'right' }}>ACTIONS</div>
            </div>

            {mainNavItems.length === 0 ? (
              <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                No items in Main Nav Bar. Drag items here or click "Add Nav Item".
              </div>
            ) : (
              <div className="sortable-list" style={{ border: 'none', borderRadius: 0 }}>
                {mainNavItems.map((item) => (
                  <div
                    key={item.id}
                    className="sortable-row"
                    draggable
                    onDragStart={(e) => handleDragStart(e, item.id)}
                    onDrop={(e) => handleDropOnCard(e, item.id, false)}
                    style={{
                      opacity: draggedId === item.id ? 0.4 : 1,
                      background: 'var(--surface)',
                    }}
                  >
                    <span className="drag-handle" title="Drag to reorder or move between sections">
                      ⠿
                    </span>
                    <div className="sortable-row-content">
                      <div className="row-grid" style={{ gridTemplateColumns: '1fr 1.5fr auto', padding: '10px 14px' }}>
                        <div className="row-cell" style={{ fontWeight: '600', color: 'var(--text)' }}>
                          {item.label}
                        </div>
                        <div className="row-cell" style={{ fontFamily: 'monospace', color: 'var(--text-muted)', fontSize: '12.5px' }}>
                          {item.url}
                        </div>
                        <div className="row-actions" style={{ display: 'flex', alignItems: 'center', gap: '6px', justifyContent: 'flex-end' }}>
                          <button
                            type="button"
                            className="btn btn-ghost btn-small"
                            onClick={() => handleToggleBucket(item.id, true)}
                            title="Move item to 'More ∨' dropdown"
                            style={{ color: 'var(--primary)', fontWeight: '600' }}
                          >
                            To More ∨
                          </button>
                          <button type="button" className="btn btn-ghost btn-small" onClick={() => handleOpenEditModal(item)}>
                            Edit
                          </button>
                          <button type="button" className="btn btn-danger btn-small" onClick={() => handleDeleteItem(item.id, item.label)}>
                            Delete
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ================= CONTAINER 2: MORE DROPDOWN ITEMS ================= */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyBetween: 'space-between', marginBottom: '10px' }}>
            <h2 style={{ fontSize: '13px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>Heading: "More ∨" Dropdown Links</span>
              <span style={{ background: '#f3e8ff', color: '#6b21a8', padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: '700' }}>
                {moreNavItems.length}
              </span>
            </h2>
          </div>

          <div
            style={{
              background: dragOverBucket === 'more' ? 'rgba(147, 51, 234, 0.04)' : 'var(--surface)',
              border: dragOverBucket === 'more' ? '2px dashed #9333ea' : '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              overflow: 'hidden',
              boxShadow: 'var(--shadow-xs)',
              transition: 'all 0.15s ease',
            }}
            onDragOver={(e) => handleDragOverContainer(e, 'more')}
            onDragLeave={handleDragLeaveContainer}
            onDrop={(e) => handleDropOnBucket(e, true)}
          >
            <div
              className="row-grid row-grid-head"
              style={{ gridTemplateColumns: '1fr 1.5fr auto', background: 'var(--surface-hover)', borderBottom: '1px solid var(--border)' }}
            >
              <div className="row-cell">LABEL</div>
              <div className="row-cell">URL</div>
              <div className="row-cell" style={{ textAlign: 'right' }}>ACTIONS</div>
            </div>

            {moreNavItems.length === 0 ? (
              <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                No items inside "More" dropdown. Drag items here from above to place under More.
              </div>
            ) : (
              <div className="sortable-list" style={{ border: 'none', borderRadius: 0 }}>
                {moreNavItems.map((item) => (
                  <div
                    key={item.id}
                    className="sortable-row"
                    draggable
                    onDragStart={(e) => handleDragStart(e, item.id)}
                    onDrop={(e) => handleDropOnCard(e, item.id, true)}
                    style={{
                      opacity: draggedId === item.id ? 0.4 : 1,
                      background: 'var(--surface)',
                    }}
                  >
                    <span className="drag-handle" title="Drag to reorder or move between sections">
                      ⠿
                    </span>
                    <div className="sortable-row-content">
                      <div className="row-grid" style={{ gridTemplateColumns: '1fr 1.5fr auto', padding: '10px 14px' }}>
                        <div className="row-cell" style={{ fontWeight: '600', color: 'var(--text)' }}>
                          {item.label}
                        </div>
                        <div className="row-cell" style={{ fontFamily: 'monospace', color: 'var(--text-muted)', fontSize: '12.5px' }}>
                          {item.url}
                        </div>
                        <div className="row-actions" style={{ display: 'flex', alignItems: 'center', gap: '6px', justifyContent: 'flex-end' }}>
                          <button
                            type="button"
                            className="btn btn-ghost btn-small"
                            onClick={() => handleToggleBucket(item.id, false)}
                            title="Move item to main Nav Bar"
                            style={{ color: '#059669', fontWeight: '600' }}
                          >
                            To Nav Bar 🌐
                          </button>
                          <button type="button" className="btn btn-ghost btn-small" onClick={() => handleOpenEditModal(item)}>
                            Edit
                          </button>
                          <button type="button" className="btn btn-danger btn-small" onClick={() => handleDeleteItem(item.id, item.label)}>
                            Delete
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* CREATE / EDIT MODAL - Native Admin Modal */}
      {modalOpen && (
        <div className="modal-backdrop">
          <div className="modal-card" style={{ maxWidth: '440px' }}>
            <div className="modal-header">
              <h2>{editingItem ? 'Edit Nav Item' : 'Add Nav Item'}</h2>
              <button type="button" className="modal-close" onClick={() => setModalOpen(false)}>
                <X size={18} aria-hidden="true" />
              </button>
            </div>

            <form onSubmit={handleSaveModal}>
              <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div className="form-group">
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '6px' }}>
                    Label
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Media & Gallery"
                    value={formData.label}
                    onChange={(e) => setFormData({ ...formData, label: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '13.5px' }}
                  />
                </div>

                <div className="form-group">
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '6px' }}>
                    URL
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. /media"
                    value={formData.url}
                    onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '13.5px', fontFamily: 'monospace' }}
                  />
                </div>

                <div className="form-group">
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '6px' }}>
                    Placement
                  </label>
                  <select
                    value={formData.in_more ? 'more' : 'main'}
                    onChange={(e) => setFormData({ ...formData, in_more: e.target.value === 'more' })}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '13.5px' }}
                  >
                    <option value="main">🌐 Main Nav Bar Links</option>
                    <option value="more">📂 Heading: "More ∨" Dropdown</option>
                  </select>
                </div>
              </div>

              <div className="modal-actions" style={{ padding: '16px 24px', background: 'var(--surface-hover)', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingItem ? 'Save Changes' : 'Add Item'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
