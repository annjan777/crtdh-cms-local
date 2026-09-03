import { Settings } from 'lucide-react';
import SingletonFormPage from './SingletonFormPage';

const FIELDS = [
  { name: 'address', label: 'Address', type: 'textarea' },
  { name: 'phone_primary', label: 'Primary Phone', type: 'text' },
  { name: 'phone_secondary', label: 'Secondary Phone', type: 'text' },
  { name: 'email_primary', label: 'Primary Email', type: 'text' },
  { name: 'email_secondary', label: 'Secondary Email', type: 'text' },
  { name: 'map_embed_url', label: 'Map Embed URL', type: 'text' },
  { name: 'facebook_url', label: 'Facebook URL', type: 'text' },
  { name: 'linkedin_url', label: 'LinkedIn URL', type: 'text' },
  { name: 'instagram_url', label: 'Instagram URL', type: 'text' },
  { name: 'twitter_url', label: 'Twitter URL', type: 'text' },
  { name: 'site_logo', label: 'CRTDH Logo (header mark)', type: 'image' },
  { name: 'logo_left', label: 'IIT Kharagpur Crest (header, left)', type: 'image' },
  { name: 'logo_right', label: 'DSIR Emblem (header, right)', type: 'image' },
];

// Site settings is a singleton (get_or_create pk=1) — no list, no
// reorder, no id-based routing — so it goes through SingletonFormPage
// rather than the id-based ResourceCrudPage flow.
export default function SiteSettingsPage() {
  return (
    <SingletonFormPage
      title="Site Settings"
      description="Contact details, map, social links, and the logos shown in the header on every page."
      icon={Settings}
      endpoint="/site-settings/"
      fields={FIELDS}
    />
  );
}
