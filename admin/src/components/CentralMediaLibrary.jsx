import { useState, useEffect, useMemo } from 'react';
import { Search, Filter, Image as ImageIcon, Trash2, ExternalLink, AlertTriangle, CheckCircle2, Copy } from 'lucide-react';
import { fetchList, deleteOne } from '../api/client';
import { useToast } from '../context/ToastContext';

export default function CentralMediaLibrary() {
  const [mediaItems, setMediaItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [selectedAsset, setSelectedAsset] = useState(null);
  const { addToast } = useToast();

  const loadMedia = async () => {
    setLoading(true);
    try {
      const [slides, team, gallery, innov, equip, site] = await Promise.all([
        fetchList('/hero-slides/').catch(() => []),
        fetchList('/team-members/').catch(() => []),
        fetchList('/media-event-images/').catch(() => []),
        fetchList('/innovation-images/').catch(() => []),
        fetchList('/equipment/').catch(() => []),
        fetchList('/site-settings/').catch(() => []),
      ]);

      const items = [];

      if (Array.isArray(slides)) {
        slides.forEach((s) => {
          if (s.image) {
            items.push({
              url: s.image,
              name: s.image.split('/').pop(),
              category: 'Hero Slides',
              usedIn: `Home → Hero Carousel → Slide ${s.id}`,
              type: 'hero',
              id: s.id,
            });
          }
        });
      }

      if (Array.isArray(team)) {
        team.forEach((m) => {
          if (m.photo) {
            items.push({
              url: m.photo,
              name: m.photo.split('/').pop(),
              category: 'Team Members',
              usedIn: `Team → Member: ${m.name}`,
              type: 'team',
              id: m.id,
            });
          }
        });
      }

      if (Array.isArray(gallery)) {
        gallery.forEach((g) => {
          if (g.image) {
            items.push({
              url: g.image,
              name: g.image.split('/').pop(),
              category: 'Gallery Events',
              usedIn: `Media → Gallery Image #${g.id}`,
              type: 'gallery',
              id: g.id,
            });
          }
        });
      }

      if (Array.isArray(innov)) {
        innov.forEach((i) => {
          if (i.image) {
            items.push({
              url: i.image,
              name: i.image.split('/').pop(),
              category: 'Innovations',
              usedIn: `Innovations → Innovation Image #${i.id}`,
              type: 'innovation',
              id: i.id,
            });
          }
        });
      }

      if (Array.isArray(equip)) {
        equip.forEach((eq) => {
          if (eq.image) {
            items.push({
              url: eq.image,
              name: eq.image.split('/').pop(),
              category: 'Facilities',
              usedIn: `Facilities → Equipment: ${eq.name}`,
              type: 'equipment',
              id: eq.id,
            });
          }
        });
      }

      setMediaItems(items);
      if (items.length > 0) setSelectedAsset(items[0]);
    } catch (err) {
      addToast('Failed to load media assets', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMedia();
  }, []);

  const filteredItems = useMemo(() => {
    return mediaItems.filter((item) => {
      const matchesSearch =
        !searchQuery ||
        item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.usedIn.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCat = activeCategory === 'all' || item.category === activeCategory;
      return matchesSearch && matchesCat;
    });
  }, [mediaItems, searchQuery, activeCategory]);

  const handleCopyUrl = (url) => {
    navigator.clipboard.writeText(url);
    addToast('Image URL copied to clipboard', 'success');
  };

  return (
    <div className="central-media-library">
      <div className="manager-header">
        <div>
          <h1 className="manager-title">Central Media Library</h1>
          <p className="manager-desc">
            Inspect, search, and track image dependencies across your entire website.
          </p>
        </div>
      </div>

      <div className="media-toolbar">
        <div className="search-box">
          <Search size={16} />
          <input
            type="text"
            placeholder="Search assets by filename or location..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="category-filter-chips">
          {['all', 'Hero Slides', 'Team Members', 'Gallery Events', 'Innovations', 'Facilities'].map((cat) => (
            <button
              key={cat}
              className={`chip ${activeCategory === cat ? 'active' : ''}`}
              onClick={() => setActiveCategory(cat)}
            >
              {cat === 'all' ? 'All Media' : cat}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="manager-loading">Scanning asset registry...</div>
      ) : filteredItems.length === 0 ? (
        <div className="manager-empty">
          <ImageIcon size={36} />
          <h3>No Media Assets Found</h3>
          <p>Try clearing your search query or filter.</p>
        </div>
      ) : (
        <div className="media-workspace">
          <div className="media-grid-container">
            <div className="media-grid">
              {filteredItems.map((asset, idx) => (
                <div
                  key={idx}
                  className={`media-tile ${selectedAsset?.url === asset.url ? 'selected' : ''}`}
                  onClick={() => setSelectedAsset(asset)}
                >
                  <img src={asset.url} alt={asset.name} />
                  <span className="media-tile-cat">{asset.category}</span>
                </div>
              ))}
            </div>
          </div>

          {selectedAsset && (
            <div className="media-inspector">
              <div className="inspector-preview">
                <img src={selectedAsset.url} alt={selectedAsset.name} />
              </div>

              <div className="inspector-meta">
                <h3 className="inspector-filename">{selectedAsset.name}</h3>
                <span className="inspector-badge">{selectedAsset.category}</span>

                <div className="inspector-used-in mt-4">
                  <span className="label">USED IN WEBSITE LOCATION:</span>
                  <div className="used-in-box">
                    <CheckCircle2 size={16} className="text-success" />
                    <span>{selectedAsset.usedIn}</span>
                  </div>
                </div>

                <div className="inspector-actions mt-6">
                  <button onClick={() => handleCopyUrl(selectedAsset.url)} className="btn btn--outline btn--sm flex-1">
                    <Copy size={14} /> Copy URL
                  </button>
                  <a href={selectedAsset.url} target="_blank" rel="noreferrer" className="btn btn--outline btn--sm">
                    <ExternalLink size={14} /> View Full
                  </a>
                </div>

                <div className="warning-callout mt-4">
                  <AlertTriangle size={16} />
                  <span>This image is actively referenced on your public site. Replacing or deleting it in CMS will update the live site.</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
