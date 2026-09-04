import { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Eye, ExternalLink, GripVertical, ArrowLeft, ArrowRight, CheckCircle2, AlertCircle } from 'lucide-react';
import { fetchList, createOne, updateOne, deleteOne, uploadFile, PUBLIC_SITE_URL } from '../api/client';
import { useToast } from '../context/ToastContext';
import LivePreviewPane from './LivePreviewPane';

export default function HeroCarouselManager() {
  const [slides, setSlides] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeSlide, setActiveSlide] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState(null);
  const [dragOverIndex, setDragOverIndex] = useState(null);
  const { addToast } = useToast();

  const loadSlides = async () => {
    setLoading(true);
    try {
      const data = await fetchList('/hero-slides/');
      setSlides(Array.isArray(data) ? data : []);
    } catch (err) {
      addToast('Failed to load hero slides', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSlides();
  }, []);

  const handleCreateNew = () => {
    setActiveSlide({
      primary_button_label: 'Explore Innovations',
      primary_button_link: '/innovations',
      secondary_button_label: 'About CRTDH',
      secondary_button_link: '/about',
      image: '',
      is_published: true,
      order: slides.length + 1,
    });
    setIsEditing(true);
  };

  const handleEdit = (slide) => {
    setActiveSlide({ ...slide });
    setIsEditing(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this Hero Slide?')) return;
    try {
      await deleteOne('/hero-slides/', id);
      addToast('Hero slide deleted successfully', 'success');
      loadSlides();
    } catch (err) {
      addToast('Failed to delete hero slide', 'error');
    }
  };

  const handleMove = async (index, direction) => {
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= slides.length) return;

    const newSlides = [...slides];
    const temp = newSlides[index];
    newSlides[index] = newSlides[targetIndex];
    newSlides[targetIndex] = temp;

    setSlides(newSlides);

    try {
      await Promise.all(
        newSlides.map((slide, idx) => updateOne('/hero-slides/', slide.id, { order: idx + 1 }))
      );
      addToast('Slide order updated!', 'success');
    } catch (err) {
      addToast('Failed to save slide order', 'error');
      loadSlides();
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

    const newSlides = [...slides];
    const [movedSlide] = newSlides.splice(draggedIndex, 1);
    newSlides.splice(targetIndex, 0, movedSlide);

    setSlides(newSlides);
    setDraggedIndex(null);

    try {
      await Promise.all(
        newSlides.map((slide, idx) => updateOne('/hero-slides/', slide.id, { order: idx + 1 }))
      );
      addToast('Slide order updated!', 'success');
    } catch (err) {
      addToast('Failed to save new slide order', 'error');
      loadSlides();
    }
  };

  const handleImageUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const previewUrl = URL.createObjectURL(file);
    setActiveSlide((prev) => ({
      ...prev,
      image: file,
      image_preview: previewUrl,
    }));
    addToast('Image attached. Click Save to upload.', 'info');
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!activeSlide.image) {
      addToast('Please upload or provide a slide image', 'error');
      return;
    }
    setSaving(true);
    try {
      if (activeSlide.id) {
        await updateOne('/hero-slides/', activeSlide.id, activeSlide);
        addToast('Hero slide updated successfully', 'success');
      } else {
        await createOne('/hero-slides/', activeSlide);
        addToast('Hero slide created successfully', 'success');
      }
      setIsEditing(false);
      loadSlides();
    } catch (err) {
      addToast('Failed to save hero slide', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="hero-manager">
      <div className="manager-header">
        <div>
          <h1 className="manager-title">Hero Carousel Manager</h1>
          <p className="manager-desc">
            Manage main visual slides and headings displayed on the public CRTDH home page.
          </p>
        </div>
        <div className="manager-actions">
          <a
            href={PUBLIC_SITE_URL}
            target="_blank"
            rel="noreferrer"
            className="btn btn--outline"
          >
            <ExternalLink size={16} /> View on Public Website
          </a>
          <button onClick={handleCreateNew} className="btn btn--primary">
            <Plus size={16} /> Add Hero Slide
          </button>
        </div>
      </div>

      {loading ? (
        <div className="manager-loading">Loading hero slides...</div>
      ) : slides.length === 0 ? (
        <div className="manager-empty">
          <AlertCircle size={36} />
          <h3>No Hero Slides Found</h3>
          <p>Create your first hero slide to customize the homepage carousel.</p>
          <button onClick={handleCreateNew} className="btn btn--primary mt-4">
            <Plus size={16} /> Add Hero Slide
          </button>
        </div>
      ) : (
        <div className="slides-grid">
          {slides.map((slide, idx) => (
            <div
              key={slide.id}
              onDragOver={(e) => handleDragOver(e, idx)}
              onDrop={(e) => handleDrop(e, idx)}
              className={`slide-card ${draggedIndex === idx ? 'is-dragging' : ''} ${dragOverIndex === idx ? 'is-drag-over' : ''}`}
            >
              <div className="slide-card-top-bar">
                <div
                  draggable
                  onDragStart={(e) => handleDragStart(e, idx)}
                  onDragEnd={() => {
                    setDraggedIndex(null);
                    setDragOverIndex(null);
                  }}
                  className="card-grip-handle"
                  title="Click & Drag to reorder card"
                >
                  <GripVertical size={15} />
                  <span>Drag</span>
                </div>

                <div className="card-order-controls">
                  <button
                    type="button"
                    disabled={idx === 0}
                    onClick={() => handleMove(idx, -1)}
                    title="Move Left (Earlier in carousel)"
                    className="order-btn"
                  >
                    <ArrowLeft size={13} />
                  </button>
                  <span className="slide-order-number">#{idx + 1}</span>
                  <button
                    type="button"
                    disabled={idx === slides.length - 1}
                    onClick={() => handleMove(idx, 1)}
                    title="Move Right (Later in carousel)"
                    className="order-btn"
                  >
                    <ArrowRight size={13} />
                  </button>
                </div>
              </div>

              <div className="slide-card-image">
                <img src={slide.image} alt={slide.heading || 'Slide image'} />
                <span className={`slide-status-badge ${slide.is_published !== false ? 'published' : 'draft'}`}>
                  {slide.is_published !== false ? 'Published' : 'Draft'}
                </span>
              </div>

              <div className="slide-card-body flex justify-end p-3">
                <div className="slide-actions flex gap-2">
                  <button onClick={() => handleEdit(slide)} className="btn-icon-sm btn-icon--primary" title="Edit Slide">
                    <Edit2 size={14} /> Edit
                  </button>
                  <button onClick={() => handleDelete(slide.id)} className="btn-icon-sm btn-icon--danger" title="Delete Slide">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Slide Editor Modal with Live Preview */}
      {isEditing && activeSlide && (
        <div className="modal-backdrop" onClick={() => setIsEditing(false)}>
          <div className="modal-card modal-card--lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{activeSlide.id ? 'Edit Hero Slide' : 'Create New Hero Slide'}</h2>
              <button className="modal-close" onClick={() => setIsEditing(false)}>&times;</button>
            </div>

            <div className="modal-split">
              <form onSubmit={handleSave} className="modal-form-pane">
                <div className="form-group">
                  <label>Slide Image *</label>
                  <div className="image-picker-zone">
                    {(activeSlide.image || activeSlide.image_preview) && (
                      <img
                        src={typeof activeSlide.image === 'string' ? activeSlide.image : activeSlide.image_preview}
                        alt="Preview"
                        className="image-picker-preview"
                        style={{ maxHeight: '140px', objectFit: 'cover', width: '100%', borderRadius: '8px', border: '1px solid #cbd5e1' }}
                      />
                    )}
                    <input type="file" accept="image/*" onChange={handleImageUpload} disabled={uploading} />
                    <span className="form-hint">{uploading ? 'Uploading image...' : 'Click to select or replace slide image'}</span>
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group flex-1">
                    <label>Primary Button Text</label>
                    <input
                      type="text"
                      value={activeSlide.primary_button_label || ''}
                      onChange={(e) => setActiveSlide({ ...activeSlide, primary_button_label: e.target.value })}
                    />
                  </div>
                  <div className="form-group flex-1">
                    <label>Primary Button Link</label>
                    <input
                      type="text"
                      value={activeSlide.primary_button_link || ''}
                      onChange={(e) => setActiveSlide({ ...activeSlide, primary_button_link: e.target.value })}
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group flex-1">
                    <label>Secondary Button Text</label>
                    <input
                      type="text"
                      value={activeSlide.secondary_button_label || ''}
                      onChange={(e) => setActiveSlide({ ...activeSlide, secondary_button_label: e.target.value })}
                    />
                  </div>
                  <div className="form-group flex-1">
                    <label>Secondary Button Link</label>
                    <input
                      type="text"
                      value={activeSlide.secondary_button_link || ''}
                      onChange={(e) => setActiveSlide({ ...activeSlide, secondary_button_link: e.target.value })}
                    />
                  </div>
                </div>

                <div className="form-checkbox-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={activeSlide.is_published !== false}
                      onChange={(e) => setActiveSlide({ ...activeSlide, is_published: e.target.checked })}
                    />
                    Publish this slide on public homepage
                  </label>
                </div>

                <div className="modal-actions">
                  <button type="button" className="btn btn--outline" onClick={() => setIsEditing(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn--primary" disabled={saving || uploading}>
                    {saving ? 'Saving...' : 'Save Slide Changes'}
                  </button>
                </div>
              </form>

              <div className="modal-preview-pane">
                <LivePreviewPane type="hero" data={activeSlide} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
