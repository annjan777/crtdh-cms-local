import { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Image as ImageIcon, Upload, ExternalLink, MoveUp, MoveDown, Calendar } from 'lucide-react';
import { fetchList, createOne, updateOne, deleteOne, uploadFile, PUBLIC_SITE_URL } from '../api/client';
import { useToast } from '../context/ToastContext';

export default function MediaGalleryManager() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeEvent, setActiveEvent] = useState(null);
  const [eventImages, setEventImages] = useState([]);
  const [isEditingEvent, setIsEditingEvent] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploadingBulk, setUploadingBulk] = useState(false);
  const { addToast } = useToast();

  const loadEvents = async () => {
    setLoading(true);
    try {
      const data = await fetchList('/media-events/');
      setEvents(Array.isArray(data) ? data : []);
    } catch (err) {
      addToast('Failed to load media events', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, []);

  const handleEditEvent = async (event) => {
    setActiveEvent({ ...event });
    setIsEditingEvent(true);
    try {
      const imagesData = await fetchList(`/media-event-images/?event=${event.id}`);
      setEventImages(Array.isArray(imagesData) ? imagesData : []);
    } catch (err) {
      setEventImages([]);
    }
  };

  const handleCreateEvent = () => {
    setActiveEvent({
      title: '',
      slug: '',
      order: events.length + 1,
    });
    setEventImages([]);
    setIsEditingEvent(true);
  };

  const handleDeleteEvent = async (id) => {
    if (!window.confirm('Delete this entire gallery event and all its photos?')) return;
    try {
      await deleteOne('/media-events/', id);
      addToast('Media event deleted', 'success');
      loadEvents();
    } catch (err) {
      addToast('Failed to delete event', 'error');
    }
  };

  const handleBulkUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    if (!activeEvent.id) {
      addToast('Please save event title first before uploading images', 'error');
      return;
    }

    setUploadingBulk(true);
    let successCount = 0;

    for (const file of files) {
      try {
        const media = await uploadFile(file);
        await createOne('/media-event-images/', {
          event: activeEvent.id,
          image: media.url,
          caption: file.name.replace(/\.[^/.]+$/, ''),
          order: eventImages.length + successCount + 1,
        });
        successCount += 1;
      } catch (err) {
        console.error('Failed to upload image:', file.name, err);
      }
    }

    setUploadingBulk(false);
    addToast(`Successfully uploaded ${successCount} images`, 'success');

    // Refresh images
    const imagesData = await fetchList(`/media-event-images/?event=${activeEvent.id}`);
    setEventImages(Array.isArray(imagesData) ? imagesData : []);
  };

  const handleDeleteImage = async (imageId) => {
    try {
      await deleteOne('/media-event-images/', imageId);
      setEventImages((prev) => prev.filter((img) => img.id !== imageId));
      addToast('Image removed', 'success');
    } catch (err) {
      addToast('Failed to delete image', 'error');
    }
  };

  const handleSaveEvent = async (e) => {
    e.preventDefault();
    if (!activeEvent.title.trim()) {
      addToast('Event title is required', 'error');
      return;
    }
    const slug = activeEvent.slug || activeEvent.title.toLowerCase().replace(/[^a-z0-9]+/g, '-');
    setSaving(true);
    try {
      if (activeEvent.id) {
        await updateOne('/media-events/', activeEvent.id, { ...activeEvent, slug });
        addToast('Event saved successfully', 'success');
      } else {
        const created = await createOne('/media-events/', { ...activeEvent, slug });
        setActiveEvent(created);
        addToast('Event created! You can now bulk upload photos below', 'success');
      }
      loadEvents();
    } catch (err) {
      addToast('Failed to save event', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="media-gallery-manager">
      <div className="manager-header">
        <div>
          <h1 className="manager-title">Media & Gallery Manager</h1>
          <p className="manager-desc">
            Create photo gallery events, upload images in bulk, set captions, and manage public media coverage.
          </p>
        </div>
        <div className="manager-actions">
          <a
            href={`${PUBLIC_SITE_URL}/media`}
            target="_blank"
            rel="noreferrer"
            className="btn btn--outline"
          >
            <ExternalLink size={16} /> View Media Page
          </a>
          <button onClick={handleCreateEvent} className="btn btn--primary">
            <Plus size={16} /> Create Gallery Event
          </button>
        </div>
      </div>

      {loading ? (
        <div className="manager-loading">Loading media events...</div>
      ) : events.length === 0 ? (
        <div className="manager-empty">
          <ImageIcon size={36} />
          <h3>No Gallery Events Found</h3>
          <p>Create a gallery event to showcase workshops, lab visits, and foundation camps.</p>
        </div>
      ) : (
        <div className="events-grid">
          {events.map((event) => (
            <div key={event.id} className="event-card">
              <div className="event-card-header">
                <div className="event-icon">
                  <Calendar size={20} />
                </div>
                <div>
                  <h3 className="event-title">{event.title}</h3>
                  <span className="event-slug">/{event.slug}</span>
                </div>
              </div>
              <div className="event-card-actions">
                <button onClick={() => handleEditEvent(event)} className="btn btn--outline btn--sm">
                  <Edit2 size={14} /> Manage Event & Photos
                </button>
                <button onClick={() => handleDeleteEvent(event.id)} className="btn-icon-sm btn-icon--danger">
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Event & Bulk Photo Editor Modal */}
      {isEditingEvent && activeEvent && (
        <div className="modal-backdrop" onClick={() => setIsEditingEvent(false)}>
          <div className="modal-card modal-card--lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{activeEvent.id ? `Manage Event: ${activeEvent.title}` : 'Create New Gallery Event'}</h2>
              <button className="modal-close" onClick={() => setIsEditingEvent(false)}>&times;</button>
            </div>

            <div className="modal-body-scroll">
              <form onSubmit={handleSaveEvent} className="event-meta-form">
                <div className="form-row">
                  <div className="form-group flex-2">
                    <label>Event Title *</label>
                    <input
                      type="text"
                      required
                      value={activeEvent.title || ''}
                      onChange={(e) => setActiveEvent({ ...activeEvent, title: e.target.value })}
                      placeholder="e.g. Pathology & Eye Clinic Camp"
                    />
                  </div>
                  <div className="form-group flex-1">
                    <label>URL Slug</label>
                    <input
                      type="text"
                      value={activeEvent.slug || ''}
                      onChange={(e) => setActiveEvent({ ...activeEvent, slug: e.target.value })}
                      placeholder="e.g. pathology-eye-clinic"
                    />
                  </div>
                  <div className="form-group flex-none flex-align-end">
                    <button type="submit" className="btn btn--primary" disabled={saving}>
                      {saving ? 'Saving...' : activeEvent.id ? 'Update Event Details' : 'Save & Continue'}
                    </button>
                  </div>
                </div>
              </form>

              {activeEvent.id && (
                <div className="bulk-upload-section mt-6">
                  <div className="section-title-bar">
                    <div>
                      <h3>Event Photos ({eventImages.length})</h3>
                      <p className="form-hint">Upload multiple images at once for this gallery event.</p>
                    </div>
                    <label className="btn btn--accent cursor-pointer">
                      <Upload size={16} /> Bulk Upload Photos
                      <input
                        type="file"
                        multiple
                        accept="image/*"
                        onChange={handleBulkUpload}
                        disabled={uploadingBulk}
                        style={{ display: 'none' }}
                      />
                    </label>
                  </div>

                  {uploadingBulk && <div className="upload-progress">Uploading images to media library...</div>}

                  {eventImages.length === 0 ? (
                    <div className="dropzone-box mt-4">
                      <ImageIcon size={32} />
                      <p>No photos uploaded to this event yet.</p>
                      <label className="btn btn--outline btn--sm mt-2 cursor-pointer">
                        Select Photos to Upload
                        <input
                          type="file"
                          multiple
                          accept="image/*"
                          onChange={handleBulkUpload}
                          style={{ display: 'none' }}
                        />
                      </label>
                    </div>
                  ) : (
                    <div className="gallery-photos-grid mt-4">
                      {eventImages.map((imgItem) => (
                        <div key={imgItem.id} className="gallery-photo-thumb">
                          <img src={imgItem.image} alt={imgItem.caption || 'Event photo'} />
                          <input
                            type="text"
                            className="caption-input"
                            value={imgItem.caption || ''}
                            placeholder="Add photo caption..."
                            onChange={async (e) => {
                              const newCaption = e.target.value;
                              setEventImages((prev) =>
                                prev.map((item) => (item.id === imgItem.id ? { ...item, caption: newCaption } : item))
                              );
                              await updateOne('/media-event-images/', imgItem.id, { caption: newCaption });
                            }}
                          />
                          <button
                            className="btn-delete-photo"
                            onClick={() => handleDeleteImage(imgItem.id)}
                            title="Delete photo"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="modal-actions">
              <button type="button" className="btn btn--outline" onClick={() => setIsEditingEvent(false)}>
                Done & Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
