import { useState, useEffect, useMemo } from 'react';
import { Plus, Edit2, Trash2, ExternalLink, GripVertical, ArrowLeft, ArrowRight, User, Users } from 'lucide-react';
import { fetchList, createOne, updateOne, deleteOne, uploadFile, PUBLIC_SITE_URL } from '../api/client';
import { useToast } from '../context/ToastContext';
import LivePreviewPane from './LivePreviewPane';

export default function TeamManager() {
  const [members, setMembers] = useState([]);
  const [categories, setCategories] = useState([]);
  const [activeCategory, setActiveCategory] = useState('all');
  const [loading, setLoading] = useState(true);
  const [activeMember, setActiveMember] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState(null);
  const [dragOverIndex, setDragOverIndex] = useState(null);
  const { addToast } = useToast();

  const loadData = async () => {
    setLoading(true);
    try {
      const [catsRes, memsRes] = await Promise.all([
        fetchList('/team-categories/'),
        fetchList('/team-members/'),
      ]);
      setCategories(Array.isArray(catsRes) ? catsRes : []);
      setMembers(Array.isArray(memsRes) ? memsRes : []);
    } catch (err) {
      addToast('Failed to load team members', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredMembers = useMemo(() => {
    if (activeCategory === 'all') return members;
    return members.filter((m) => String(m.category) === String(activeCategory));
  }, [members, activeCategory]);

  const handleCreateNew = () => {
    const defaultCat = categories[0]?.id || 1;
    setActiveMember({
      name: '',
      category: defaultCat,
      photo: '',
      designation: '',
      institution: 'IIT Kharagpur',
      description: '',
      order: members.length + 1,
    });
    setIsEditing(true);
  };

  const handleEdit = (member) => {
    setActiveMember({ ...member });
    setIsEditing(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this team member?')) return;
    try {
      await deleteOne('/team-members/', id);
      addToast('Team member deleted successfully', 'success');
      loadData();
    } catch (err) {
      addToast('Failed to delete team member', 'error');
    }
  };

  const handleMove = async (index, direction) => {
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= filteredMembers.length) return;

    const list = [...filteredMembers];
    const temp = list[index];
    list[index] = list[targetIndex];
    list[targetIndex] = temp;

    setMembers(list);

    try {
      await Promise.all(
        list.map((mem, idx) => updateOne('/team-members/', mem.id, { order: idx + 1 }))
      );
      addToast('Member order updated!', 'success');
      loadData();
    } catch (err) {
      addToast('Failed to reorder members', 'error');
    }
  };

  const handleDragStart = (e, index) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(index));
  };

  const handleDragOver = (e, index) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (dragOverIndex !== index) {
      setDragOverIndex(index);
    }
  };

  const handleDrop = async (e, targetIndex) => {
    e.preventDefault();
    setDragOverIndex(null);
    if (draggedIndex === null || draggedIndex === targetIndex) return;

    const list = [...filteredMembers];
    const [movedMember] = list.splice(draggedIndex, 1);
    list.splice(targetIndex, 0, movedMember);

    setMembers(list);
    setDraggedIndex(null);

    try {
      await Promise.all(
        list.map((mem, idx) => updateOne('/team-members/', mem.id, { order: idx + 1 }))
      );
      addToast('Team members reordered!', 'success');
      loadData();
    } catch (err) {
      addToast('Failed to reorder members', 'error');
    }
  };

  const handlePhotoUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const previewUrl = URL.createObjectURL(file);
    setActiveMember((prev) => ({
      ...prev,
      photo: file,
      photo_preview: previewUrl,
    }));
    addToast('Photo attached. Click Save to upload.', 'info');
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!activeMember.name.trim()) {
      addToast('Member name is required', 'error');
      return;
    }
    setSaving(true);
    try {
      if (activeMember.id) {
        await updateOne('/team-members/', activeMember.id, activeMember);
        addToast('Team member updated', 'success');
      } else {
        await createOne('/team-members/', activeMember);
        addToast('Team member created', 'success');
      }
      setIsEditing(false);
      loadData();
    } catch (err) {
      addToast('Failed to save team member', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="team-manager">
      <div className="manager-header">
        <div>
          <h1 className="manager-title">Team Management</h1>
          <p className="manager-desc">
            Organize researchers, faculty, principal investigators, and staff as displayed on the public Team page.
          </p>
        </div>
        <div className="manager-actions">
          <a
            href={`${PUBLIC_SITE_URL}/team`}
            target="_blank"
            rel="noreferrer"
            className="btn btn--outline"
          >
            <ExternalLink size={16} /> View Team Page
          </a>
          <button onClick={handleCreateNew} className="btn btn--primary">
            <Plus size={16} /> Add Team Member
          </button>
        </div>
      </div>

      {/* Role / Category Tabs */}
      <div className="category-tabs">
        <button
          className={`tab-btn ${activeCategory === 'all' ? 'active' : ''}`}
          onClick={() => setActiveCategory('all')}
        >
          All Roles ({members.length})
        </button>
        {categories.map((cat) => {
          const count = members.filter((m) => String(m.category) === String(cat.id)).length;
          return (
            <button
              key={cat.id}
              className={`tab-btn ${activeCategory === String(cat.id) ? 'active' : ''}`}
              onClick={() => setActiveCategory(String(cat.id))}
            >
              {cat.name} ({count})
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="manager-loading">Loading team members...</div>
      ) : filteredMembers.length === 0 ? (
        <div className="manager-empty">
          <Users size={36} />
          <h3>No Team Members Found</h3>
          <p>Add a new team member to populate this section on the public site.</p>
        </div>
      ) : (
        <div className="team-cards-grid">
          {filteredMembers.map((member, idx) => (
            <div
              key={member.id}
              onDragOver={(e) => handleDragOver(e, idx)}
              onDrop={(e) => handleDrop(e, idx)}
              className={`team-person-card ${draggedIndex === idx ? 'is-dragging' : ''} ${dragOverIndex === idx ? 'is-drag-over' : ''}`}
            >
              <div className="card-top-bar">
                <div
                  draggable
                  onDragStart={(e) => handleDragStart(e, idx)}
                  onDragEnd={() => {
                    setDraggedIndex(null);
                    setDragOverIndex(null);
                  }}
                  className="card-grip-handle"
                  title="Click & Drag to reorder member"
                >
                  <GripVertical size={14} />
                  <span>Drag</span>
                </div>

                <div className="card-order-controls">
                  <button
                    type="button"
                    disabled={idx === 0}
                    onClick={() => handleMove(idx, -1)}
                    title="Move Left"
                    className="order-btn"
                  >
                    <ArrowLeft size={13} />
                  </button>
                  <span className="slide-order-number">#{idx + 1}</span>
                  <button
                    type="button"
                    disabled={idx === filteredMembers.length - 1}
                    onClick={() => handleMove(idx, 1)}
                    title="Move Right"
                    className="order-btn"
                  >
                    <ArrowRight size={13} />
                  </button>
                </div>
              </div>

              <div className="team-card-inner">
                <div className="team-person-photo">
                  {member.photo ? (
                    <img src={member.photo} alt={member.name} />
                  ) : (
                    <div className="photo-fallback">
                      <User size={36} />
                    </div>
                  )}
                </div>
                <div className="team-person-content">
                  <span className="team-person-role">{member.category_name || 'Team Member'}</span>
                  <h4 className="team-person-name">{member.name}</h4>
                  {member.designation && <p className="team-person-designation">{member.designation}</p>}
                  {member.institution && <p className="team-person-institution">{member.institution}</p>}

                  <div className="team-person-actions mt-auto">
                    <div className="team-btns w-full justify-end">
                      <button onClick={() => handleEdit(member)} className="btn-icon-sm btn-icon--primary">
                        <Edit2 size={14} /> Edit
                      </button>
                      <button onClick={() => handleDelete(member.id)} className="btn-icon-sm btn-icon--danger">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Editor Modal */}
      {isEditing && activeMember && (
        <div className="modal-backdrop" onClick={() => setIsEditing(false)}>
          <div className="modal-card modal-card--lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{activeMember.id ? 'Edit Team Member' : 'Add New Team Member'}</h2>
              <button className="modal-close" onClick={() => setIsEditing(false)}>&times;</button>
            </div>

            <div className="modal-split">
              <form onSubmit={handleSave} className="modal-form-pane">
                <div className="form-group">
                  <label>Full Name *</label>
                  <input
                    type="text"
                    required
                    value={activeMember.name || ''}
                    onChange={(e) => setActiveMember({ ...activeMember, name: e.target.value })}
                    placeholder="e.g. Prof. Suman Chakraborty"
                  />
                </div>

                <div className="form-group">
                  <label>Role / Category *</label>
                  <select
                    value={activeMember.category || ''}
                    onChange={(e) => {
                      const catObj = categories.find((c) => String(c.id) === e.target.value);
                      setActiveMember({
                        ...activeMember,
                        category: e.target.value,
                        category_name: catObj?.name,
                      });
                    }}
                  >
                    {categories.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Member Photo</label>
                  <div className="image-picker-zone">
                    {activeMember.photo && (
                      <img src={activeMember.photo} alt="Preview" className="image-picker-preview avatar-preview" />
                    )}
                    <input type="file" accept="image/*" onChange={handlePhotoUpload} disabled={uploading} />
                    <span className="form-hint">
                      {uploading ? 'Uploading photo...' : 'Click to select or change member photo'}
                    </span>
                  </div>
                </div>

                <div className="form-group">
                  <label>Designation / Specialization</label>
                  <input
                    type="text"
                    value={activeMember.designation || ''}
                    onChange={(e) => setActiveMember({ ...activeMember, designation: e.target.value })}
                    placeholder="e.g. Lead Researcher & Co-PI"
                  />
                </div>

                <div className="form-group">
                  <label>Institution / Department</label>
                  <input
                    type="text"
                    value={activeMember.institution || ''}
                    onChange={(e) => setActiveMember({ ...activeMember, institution: e.target.value })}
                    placeholder="e.g. Mechanical Engineering, IIT Kharagpur"
                  />
                </div>

                <div className="modal-actions">
                  <button type="button" className="btn btn--outline" onClick={() => setIsEditing(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn--primary" disabled={saving || uploading}>
                    {saving ? 'Saving...' : 'Save Member'}
                  </button>
                </div>
              </form>

              <div className="modal-preview-pane">
                <LivePreviewPane type="team" data={activeMember} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
