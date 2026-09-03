import { Home } from 'lucide-react';
import SingletonFormPage from './SingletonFormPage';

const FIELDS = [
  { name: 'objective_text', label: 'Objective', type: 'textarea' },

  { name: 'enterprises_text', label: 'Enterprises Engagement — text', type: 'textarea' },
  { name: 'enterprises_image_1', label: 'Enterprises Engagement — image 1', type: 'image' },
  { name: 'enterprises_image_2', label: 'Enterprises Engagement — image 2', type: 'image' },
  { name: 'msme_map_image', label: 'MSME cluster map', type: 'image' },
  { name: 'msme_caption', label: 'MSME map caption', type: 'text' },

  { name: 'women_text_1', label: 'Women Empowerment — text 1', type: 'textarea' },
  { name: 'women_image_1', label: 'Women Empowerment — image 1', type: 'image' },
  { name: 'women_image_2', label: 'Women Empowerment — image 2', type: 'image' },
  { name: 'women_text_2', label: 'Women Empowerment — text 2', type: 'textarea' },

  { name: 'location_address', label: 'Location & Facility — address', type: 'text' },
  { name: 'location_description', label: 'Location & Facility — description', type: 'textarea' },

  { name: 'facility_card_1_title', label: 'Facility card 1 — title', type: 'text' },
  { name: 'facility_card_1_image', label: 'Facility card 1 — image', type: 'image' },
  { name: 'facility_card_1_link', label: 'Facility card 1 — link (optional)', type: 'text' },
  { name: 'facility_card_2_title', label: 'Facility card 2 — title', type: 'text' },
  { name: 'facility_card_2_image', label: 'Facility card 2 — image', type: 'image' },
  { name: 'facility_card_2_link', label: 'Facility card 2 — link (optional)', type: 'text' },
  { name: 'facility_card_3_title', label: 'Facility card 3 — title', type: 'text' },
  { name: 'facility_card_3_image', label: 'Facility card 3 — image', type: 'image' },
  { name: 'facility_card_3_link', label: 'Facility card 3 — link (optional)', type: 'text' },

  { name: 'chintan_shivir_youtube_id', label: 'Chintan Shivir — YouTube video ID', type: 'text', hint: 'Just the ID, e.g. PumM2298Zaw.' },
  { name: 'viksit_bharat_youtube_id', label: 'Viksit Bharat Abhiyan — YouTube video ID', type: 'text' },
  { name: 'office_image', label: 'Office photo', type: 'image' },

  { name: 'membership_heading', label: 'Membership section heading', type: 'text' },
  { name: 'membership_pdf', label: 'Membership PDF', type: 'file' },
];

// HomePage is a singleton (get_or_create pk=1) — the long-form homepage
// sections (Objective, Enterprises Engagement, Women Empowerment,
// Location & Facility, Membership) that don't fit the reusable image-grid
// content type.
export default function HomePageAdmin() {
  return (
    <SingletonFormPage
      title="Home Page"
      description="The Objective, Enterprises Engagement, Women Empowerment, Location & Facility and Membership sections on the public homepage."
      icon={Home}
      endpoint="/home-page/"
      fields={FIELDS}
    />
  );
}
