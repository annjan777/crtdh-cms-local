import { Info } from 'lucide-react';
import SingletonFormPage from './SingletonFormPage';

const FIELDS = [
  { name: 'intro', label: 'About CRTDH — intro', type: 'textarea', hint: 'Opening paragraph(s) on the About page.' },
  { name: 'mission_vision', label: 'Mission & Vision', type: 'textarea' },
  {
    name: 'focus_intro',
    label: 'Focus area taglines',
    type: 'textarea',
    hint: 'One tagline per line, shown above the Focus Area color blocks.',
  },
  { name: 'ecosystem_heading', label: 'Ecosystem panel heading', type: 'text' },
  { name: 'ecosystem_image', label: 'Ecosystem panel image', type: 'image' },
  { name: 'pi_desk_image', label: "PI's desk photo", type: 'image' },
  { name: 'pi_desk_document', label: "PI's desk document (optional)", type: 'file' },
  { name: 'dsir_about', label: 'About DSIR', type: 'textarea' },
  { name: 'iitkgp_about', label: 'About IIT Kharagpur', type: 'textarea' },
];

// AboutPage is a singleton (get_or_create pk=1), same as SiteSettings.
export default function AboutPageAdmin() {
  return (
    <SingletonFormPage
      title="About Page"
      description="The long-form prose, images and organisation notes shown on the public About page."
      icon={Info}
      endpoint="/about-page/"
      fields={FIELDS}
    />
  );
}
