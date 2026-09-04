import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Layers,
  Image as ImageIcon,
  Megaphone,
  BarChart2,
  Info,
  Target,
  Building2,
  Heart,
  MapPin,
  Video,
  FileText,
  Edit3,
  ExternalLink,
  CheckCircle2,
} from 'lucide-react';
import { fetchOne, updateOne, uploadFile, PUBLIC_SITE_URL } from '../api/client';
import { useToast } from '../context/ToastContext';
import LivePreviewPane from '../components/LivePreviewPane';

export default function HomePageSectionsEditor() {
  const [homeData, setHomeData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState(null);
  const [formData, setFormData] = useState({});
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const { addToast } = useToast();

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchOne('/home-page/');
      setHomeData(data || {});
      setFormData(data || {});
    } catch (err) {
      addToast('Failed to load Home Page content', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const openSectionEditor = (sectionKey) => {
    setActiveSection(sectionKey);
  };

  const handleFileUpload = (e, fieldName) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFormData((prev) => ({
      ...prev,
      [fieldName]: file,
      [`${fieldName}_preview`]: URL.createObjectURL(file),
    }));
    addToast('File attached. Click Save Changes to upload.', 'info');
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await updateOne('/home-page/', null, formData);
      setHomeData(updated || formData);
      setFormData(updated || formData);
      addToast('Section updated successfully', 'success');
      setActiveSection(null);
    } catch (err) {
      const data = err?.response?.data;
      if (data && typeof data === 'object') {
        const firstKey = Object.keys(data)[0];
        const firstMsg = Array.isArray(data[firstKey]) ? data[firstKey][0] : data[firstKey];
        addToast(`Save failed: ${firstKey} — ${firstMsg}`, 'error');
      } else {
        addToast('Failed to save section updates', 'error');
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="manager-loading">Loading Home Page Sections...</div>;

  return (
    <div className="homepage-sections-editor">
      <div className="manager-header">
        <div>
          <h1 className="manager-title">Home Page CMS Manager</h1>
          <p className="manager-desc">
            Edit individual sections of the public CRTDH home page independently.
          </p>
        </div>
        <div className="manager-actions">
          <a href={PUBLIC_SITE_URL} target="_blank" rel="noreferrer" className="btn btn--outline btn--sm gap-2 text-slate-300 hover:text-white">
            <ExternalLink size={16} /> View Live Home Page
          </a>
        </div>
      </div>

      <div className="section-cards-grid">
        {/* Card 1: Hero Carousel */}
        <div className="section-manage-card">
          <div className="card-head">
            <div className="card-icon"><ImageIcon size={22} /></div>
            <div>
              <h3>Hero Carousel</h3>
              <p>Top visual slides & banner headings</p>
            </div>
          </div>
          <div className="card-foot">
            <span className="card-badge">Managed Visually</span>
            <Link to="/hero-manager" className="btn btn--primary btn--sm">
              <Edit3 size={14} /> Manage Slides &rarr;
            </Link>
          </div>
        </div>

        {/* Card 2: News & Events Marquee */}
        <div className="section-manage-card">
          <div className="card-head">
            <div className="card-icon"><Megaphone size={22} /></div>
            <div>
              <h3>News & Events Ticker</h3>
              <p>Live scrolling announcements</p>
            </div>
          </div>
          <div className="card-foot">
            <span className="card-badge">Global Content</span>
            <Link to="/resources/news-items" className="btn btn--primary btn--sm">
              <Edit3 size={14} /> Manage Ticker &rarr;
            </Link>
          </div>
        </div>

        {/* Card 3: Key Statistics */}
        <div className="section-manage-card">
          <div className="card-head">
            <div className="card-icon"><BarChart2 size={22} /></div>
            <div>
              <h3>Statistics Strip</h3>
              <p>13+ Innovations, 28+ Enterprises, etc.</p>
            </div>
          </div>
          <div className="card-foot">
            <span className="card-badge">Live Auto Stats</span>
            <button onClick={() => openSectionEditor('stats')} className="btn btn--outline btn--sm">
              <Edit3 size={14} /> Edit &rarr;
            </button>
          </div>
        </div>

        {/* Card 4: Objective Section */}
        <div className="section-manage-card">
          <div className="card-head">
            <div className="card-icon"><Target size={22} /></div>
            <div>
              <h3>Objective Section</h3>
              <p>Core goals and research vision</p>
            </div>
          </div>
          <div className="card-foot">
            <span className="card-badge">Text Content</span>
            <button onClick={() => openSectionEditor('objective')} className="btn btn--outline btn--sm">
              <Edit3 size={14} /> Edit Section &rarr;
            </button>
          </div>
        </div>

        {/* Card 5: Enterprise Engagement */}
        <div className="section-manage-card">
          <div className="card-head">
            <div className="card-icon"><Building2 size={22} /></div>
            <div>
              <h3>Enterprise Engagement</h3>
              <p>MSME cluster support & map graphic</p>
            </div>
          </div>
          <div className="card-foot">
            <span className="card-badge">Text & Images</span>
            <button onClick={() => openSectionEditor('enterprises')} className="btn btn--outline btn--sm">
              <Edit3 size={14} /> Edit Section &rarr;
            </button>
          </div>
        </div>

        {/* Card 6: Rural Healthcare & Women Empowerment */}
        <div className="section-manage-card">
          <div className="card-head">
            <div className="card-icon"><Heart size={22} /></div>
            <div>
              <h3>Rural Healthcare & Empowerment</h3>
              <p>Community outreach & anemia detection</p>
            </div>
          </div>
          <div className="card-foot">
            <span className="card-badge">Text & Photos</span>
            <button onClick={() => openSectionEditor('women')} className="btn btn--outline btn--sm">
              <Edit3 size={14} /> Edit Section &rarr;
            </button>
          </div>
        </div>

        {/* Card 7: Location & Facilities */}
        <div className="section-manage-card">
          <div className="card-head">
            <div className="card-icon"><MapPin size={22} /></div>
            <div>
              <h3>Location & Facilities Cards</h3>
              <p>Diamond Jubilee Bldg & Lab cards</p>
            </div>
          </div>
          <div className="card-foot">
            <span className="card-badge">Cards & Images</span>
            <button onClick={() => openSectionEditor('location')} className="btn btn--outline btn--sm">
              <Edit3 size={14} /> Edit Section &rarr;
            </button>
          </div>
        </div>

        {/* Card 8: Videos */}
        <div className="section-manage-card">
          <div className="card-head">
            <div className="card-icon"><Video size={22} /></div>
            <div>
              <h3>Featured Videos</h3>
              <p>Chintan Shivir & Viksit Bharat video highlights</p>
            </div>
          </div>
          <div className="card-foot">
            <span className="card-badge">YouTube IDs</span>
            <button onClick={() => openSectionEditor('videos')} className="btn btn--outline btn--sm">
              <Edit3 size={14} /> Edit Videos &rarr;
            </button>
          </div>
        </div>

        {/* Card 9: Annual Membership */}
        <div className="section-manage-card">
          <div className="card-head">
            <div className="card-icon"><FileText size={22} /></div>
            <div>
              <h3>Annual Membership Callout</h3>
              <p>MSME / Startup membership PDF download</p>
            </div>
          </div>
          <div className="card-foot">
            <span className="card-badge">PDF File</span>
            <button onClick={() => openSectionEditor('membership')} className="btn btn--outline btn--sm">
              <Edit3 size={14} /> Edit Callout &rarr;
            </button>
          </div>
        </div>
      </div>

      {/* Targeted Section Editor Modal */}
      {activeSection && (
        <div className="modal-backdrop" onClick={() => setActiveSection(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Edit Section: {activeSection.toUpperCase()}</h2>
              <button className="modal-close" onClick={() => setActiveSection(null)}>&times;</button>
            </div>

            <form onSubmit={handleSave} className="modal-form-pane">
              {activeSection === 'stats' && (
                <>
                  <div className="form-row">
                    <div className="form-group flex-1">
                      <label>Innovations & Technologies Count</label>
                      <input
                        type="text"
                        value={formData.stats_innovations_count || ''}
                        onChange={(e) => setFormData({ ...formData, stats_innovations_count: e.target.value })}
                        placeholder="e.g. 15+"
                      />
                    </div>
                    <div className="form-group flex-1">
                      <label>MSMEs & Startups Supported</label>
                      <input
                        type="text"
                        value={formData.stats_msmes_supported || ''}
                        onChange={(e) => setFormData({ ...formData, stats_msmes_supported: e.target.value })}
                        placeholder="e.g. 40+"
                      />
                    </div>
                  </div>
                  <div className="form-row mt-3">
                    <div className="form-group flex-1">
                      <label>Patents & IP Filed</label>
                      <input
                        type="text"
                        value={formData.stats_patents_filed || ''}
                        onChange={(e) => setFormData({ ...formData, stats_patents_filed: e.target.value })}
                        placeholder="e.g. 10+"
                      />
                    </div>
                    <div className="form-group flex-1">
                      <label>Trainings & Workshops Conducted</label>
                      <input
                        type="text"
                        value={formData.stats_trainings_conducted || ''}
                        onChange={(e) => setFormData({ ...formData, stats_trainings_conducted: e.target.value })}
                        placeholder="e.g. 25+"
                      />
                    </div>
                  </div>
                </>
              )}

              {activeSection === 'objective' && (
                <div className="form-group">
                  <label>Objective Text</label>
                  <textarea
                    rows={6}
                    value={formData.objective_text || ''}
                    onChange={(e) => setFormData({ ...formData, objective_text: e.target.value })}
                    placeholder="Enter objective text..."
                  />
                </div>
              )}

              {activeSection === 'enterprises' && (
                <>
                  <div className="form-group">
                    <label>Enterprise Engagement Text</label>
                    <textarea
                      rows={4}
                      value={formData.enterprises_text || ''}
                      onChange={(e) => setFormData({ ...formData, enterprises_text: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>MSME Map Caption</label>
                    <input
                      type="text"
                      value={formData.msme_caption || ''}
                      onChange={(e) => setFormData({ ...formData, msme_caption: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>MSME Cluster Map Image</label>
                    <input type="file" accept="image/*" onChange={(e) => handleFileUpload(e, 'msme_map_image')} />
                    {formData.msme_map_image && <img src={formData.msme_map_image} alt="Map" className="preview-thumb mt-2" />}
                  </div>
                </>
              )}

              {activeSection === 'women' && (
                <>
                  <div className="form-group">
                    <label>Rural Healthcare Description Paragraph 1</label>
                    <textarea
                      rows={4}
                      value={formData.women_text_1 || ''}
                      onChange={(e) => setFormData({ ...formData, women_text_1: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>Rural Healthcare Description Paragraph 2</label>
                    <textarea
                      rows={4}
                      value={formData.women_text_2 || ''}
                      onChange={(e) => setFormData({ ...formData, women_text_2: e.target.value })}
                    />
                  </div>
                </>
              )}

              {activeSection === 'location' && (
                <>
                  <div className="form-group">
                    <label>Location Address Title</label>
                    <input
                      type="text"
                      value={formData.location_address || ''}
                      onChange={(e) => setFormData({ ...formData, location_address: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>Location Description</label>
                    <textarea
                      rows={3}
                      value={formData.location_description || ''}
                      onChange={(e) => setFormData({ ...formData, location_description: e.target.value })}
                    />
                  </div>
                </>
              )}

              {activeSection === 'videos' && (
                <>
                  <div className="form-group">
                    <label>Chintan Shivir YouTube Video ID</label>
                    <input
                      type="text"
                      value={formData.chintan_shivir_youtube_id || ''}
                      onChange={(e) => setFormData({ ...formData, chintan_shivir_youtube_id: e.target.value })}
                      placeholder="e.g. dQw4w9WgXcQ"
                    />
                  </div>
                  <div className="form-group">
                    <label>Viksit Bharat YouTube Video ID</label>
                    <input
                      type="text"
                      value={formData.viksit_bharat_youtube_id || ''}
                      onChange={(e) => setFormData({ ...formData, viksit_bharat_youtube_id: e.target.value })}
                      placeholder="e.g. dQw4w9WgXcQ"
                    />
                  </div>
                </>
              )}

              {activeSection === 'membership' && (
                <>
                  <div className="form-group">
                    <label>Membership Callout Heading</label>
                    <input
                      type="text"
                      value={formData.membership_heading || ''}
                      onChange={(e) => setFormData({ ...formData, membership_heading: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>Membership PDF Document</label>
                    <input type="file" accept=".pdf" onChange={(e) => handleFileUpload(e, 'membership_pdf')} />
                    {formData.membership_pdf && <span className="form-hint mt-1">Current file uploaded</span>}
                  </div>
                </>
              )}

              <div className="modal-actions mt-6">
                <button type="button" className="btn btn--outline" onClick={() => setActiveSection(null)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn--primary" disabled={saving || uploading}>
                  {saving ? 'Saving Section...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
