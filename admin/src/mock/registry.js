// Mock section registry (contract §2). The real one is exported by
// `manage.py export_registry` from backend/apps/publishing/registry.py and
// arrives in GET /api/v1/cms/pages/. This copy exists only so the admin can be
// built and tested before backend-core lands; field names match the current
// DRF serializers (see team/stub-snapshot.json).
//
// Extensions the admin relies on beyond contract §2 (sent to the lead):
//   section.description  one sentence, shown in the field panel and empty states
//   section.item_label   field(s) used to name a collection item
//   section.add_label    "Add first …" / "Add …" wording
//   section.filter       {field: value} scoping a shared resource to this page
//   section.children     nested lists (innovation photos, event photos, …)
//   field.label/help     plain-language label and help line
//   field.position_field image field: the CSS object-position field (focal point)
//   field.warn_width     image field: warn (not reject) below this width; default 1200

const img = (name, label, extra = {}) => ({
  name,
  type: 'image',
  label,
  alt_field: `${name}_alt`,
  ...extra,
});

const PAGE_CHOICES = [
  'home', 'about', 'team', 'innovations', 'facilities', 'services', 'product',
  'enterprises', 'social-impact', 'covid-19', 'media', 'contact',
];

const imageGrid = (page, columnsLabel) => ({
  id: `${page}.photo-sections`,
  label: 'Photo sections',
  kind: 'collection',
  resource: 'image-grid-blocks',
  filter: { page },
  item_label: ['section_title'],
  add_label: 'photo section',
  description: `Titled groups of photos ${columnsLabel}.`,
  fields: [
    { name: 'section_title', type: 'text', label: 'Section heading', max: 80 },
    { name: 'intro', type: 'textarea', label: 'Introduction', max: 600 },
    { name: 'page', type: 'select', label: 'Shown on page', choices: PAGE_CHOICES, required: true },
  ],
  children: [
    {
      resource: 'image-grid-items',
      parent_field: 'block',
      label: 'Photos',
      item_label: ['caption'],
      add_label: 'photo',
      fields: [img('image', 'Photo', { required: true }), { name: 'caption', type: 'text', label: 'Caption', max: 120 }],
    },
  ],
});

const videos = (page) => ({
  id: `${page}.videos`,
  label: 'Videos',
  kind: 'collection',
  resource: 'video-blocks',
  filter: { page },
  item_label: ['title'],
  add_label: 'video',
  description: 'YouTube videos embedded on this page.',
  fields: [
    { name: 'title', type: 'text', label: 'Title', max: 80, required: true },
    { name: 'youtube_url', type: 'url', label: 'YouTube link', help: 'Paste the link from the YouTube Share button.' },
    { name: 'page', type: 'select', label: 'Shown on page', choices: PAGE_CHOICES, required: true },
  ],
});

export const REGISTRY = {
  pages: [
    {
      id: 'home',
      path: '/',
      title: 'Home',
      sections: [
        {
          id: 'home.hero',
          label: 'Hero',
          kind: 'collection',
          resource: 'hero-slides',
          item_label: ['heading', 'highlight_heading'],
          item_noun: 'slide',
          add_label: 'slide',
          description: 'The large photo and headline at the top of the home page.',
          fields: [
            img('image', 'Photo', { required: true, min_width: 1600, alt_field: 'alt_text', position_field: 'image_position' }),
            { name: 'eyebrow', type: 'text', label: 'Small line above the headline', max: 40 },
            { name: 'heading', type: 'text', label: 'Headline', max: 40, required: true },
            { name: 'highlight_heading', type: 'text', label: 'Headline, highlighted part', max: 40 },
            { name: 'heading_end', type: 'text', label: 'Headline, last part', max: 30 },
            { name: 'description', type: 'textarea', label: 'Supporting line', max: 160 },
            { name: 'primary_button_label', type: 'text', label: 'Main button text', max: 24 },
            { name: 'primary_button_link', type: 'url', label: 'Main button link', help: 'A page on this site such as /innovations, or a full web address.' },
            { name: 'secondary_button_label', type: 'text', label: 'Second button text', max: 24 },
            { name: 'secondary_button_link', type: 'url', label: 'Second button link' },
          ],
        },
        {
          id: 'home.news',
          label: 'News ticker',
          kind: 'collection',
          resource: 'news-items',
          item_label: ['text'],
          add_label: 'news line',
          description: 'Short news lines that scroll under the hero.',
          fields: [
            { name: 'text', type: 'textarea', label: 'News line', max: 140, required: true },
            { name: 'link_url', type: 'url', label: 'Link', help: 'Optional. Where the line goes when clicked.' },
          ],
        },
        {
          id: 'home.objective',
          label: 'Why CRTDH exists',
          kind: 'singleton',
          resource: 'home-page',
          description: 'The opening statement under the news ticker.',
          fields: [{ name: 'objective_text', type: 'textarea', label: 'Statement', max: 900 }],
        },
        {
          id: 'home.membership',
          label: 'Membership',
          kind: 'singleton',
          resource: 'home-page',
          description: 'The annual membership call-out for MSMEs and start-ups.',
          fields: [{ name: 'membership_heading', type: 'text', label: 'Heading', max: 80 }],
        },
        {
          id: 'home.enterprises',
          label: 'Enterprises',
          kind: 'singleton',
          resource: 'home-page',
          description: 'How CRTDH works with enterprises, with two photos.',
          fields: [
            { name: 'enterprises_text', type: 'textarea', label: 'Text', max: 900 },
            img('enterprises_image_1', 'First photo'),
            img('enterprises_image_2', 'Second photo'),
          ],
        },
        {
          id: 'home.msme',
          label: 'MSME map',
          kind: 'singleton',
          resource: 'home-page',
          description: 'The map of MSMEs supported, with its caption.',
          fields: [img('msme_map_image', 'Map image'), { name: 'msme_caption', type: 'text', label: 'Caption', max: 160 }],
        },
        {
          id: 'home.rural',
          label: 'Rural healthcare',
          kind: 'singleton',
          resource: 'home-page',
          description: 'Two paragraphs and two photos on community health work.',
          fields: [
            { name: 'women_text_1', type: 'textarea', label: 'First paragraph', max: 900 },
            img('women_image_1', 'First photo'),
            { name: 'women_text_2', type: 'textarea', label: 'Second paragraph', max: 900 },
            img('women_image_2', 'Second photo'),
          ],
        },
        {
          id: 'home.facilities',
          label: 'Facility cards',
          kind: 'singleton',
          resource: 'home-page',
          description: 'Three cards linking to the facilities.',
          fields: [1, 2, 3].flatMap((n) => [
            { name: `facility_card_${n}_title`, type: 'text', label: `Card ${n} title`, max: 60 },
            img(`facility_card_${n}_image`, `Card ${n} photo`),
            { name: `facility_card_${n}_link`, type: 'url', label: `Card ${n} link` },
          ]),
        },
        {
          id: 'home.videos',
          label: 'Videos',
          kind: 'singleton',
          resource: 'home-page',
          description: 'The two featured YouTube videos.',
          fields: [
            { name: 'chintan_shivir_youtube_id', type: 'text', label: 'Chintan Shivir video ID', max: 20, help: 'The part after v= in the YouTube link.' },
            { name: 'viksit_bharat_youtube_id', type: 'text', label: 'Viksit Bharat video ID', max: 20 },
          ],
        },
        {
          id: 'home.visit',
          label: 'Visit us',
          kind: 'singleton',
          resource: 'home-page',
          description: 'Address and office photo at the bottom of the home page.',
          fields: [
            { name: 'location_address', type: 'text', label: 'Address heading', max: 160 },
            { name: 'location_description', type: 'textarea', label: 'Directions', max: 600 },
            img('office_image', 'Office photo'),
          ],
        },
      ],
    },
    {
      id: 'about',
      path: '/about',
      title: 'About',
      sections: [
        {
          id: 'about.intro',
          label: 'Introduction',
          kind: 'singleton',
          resource: 'about-page',
          description: 'What CRTDH is, its mission, and the focus-area introduction.',
          fields: [
            { name: 'intro', type: 'richtext', label: 'Introduction' },
            { name: 'mission_vision', type: 'richtext', label: 'Mission and vision' },
            { name: 'focus_intro', type: 'textarea', label: 'Focus areas introduction', max: 600 },
          ],
        },
        {
          id: 'about.focus',
          label: 'Focus areas',
          kind: 'collection',
          resource: 'focus-areas',
          item_label: ['title'],
          add_label: 'focus area',
          description: 'The coloured focus-area tiles.',
          fields: [
            { name: 'title', type: 'text', label: 'Title', max: 60, required: true },
            {
              name: 'color',
              type: 'select',
              label: 'Tile colour',
              choices: [
                { value: '#0f4c75', label: 'Navy' },
                { value: '#1a8a8a', label: 'Teal' },
                { value: '#520000', label: 'Maroon' },
                { value: '#3d4a1f', label: 'Olive' },
                { value: '#4a3b2a', label: 'Brown' },
              ],
            },
          ],
        },
        {
          id: 'about.support',
          label: 'How CRTDH supports MSMEs',
          kind: 'collection',
          resource: 'objective-rows',
          item_label: ['category', 'task'],
          add_label: 'row',
          description: 'The table of support stages, tasks and outcomes.',
          fields: [
            { name: 'category', type: 'text', label: 'Stage', max: 40, help: 'Rows with the same stage are grouped together.' },
            { name: 'task', type: 'textarea', label: 'What happens', max: 300, required: true },
            { name: 'outcome', type: 'textarea', label: 'Outcome', max: 300 },
          ],
        },
        {
          id: 'about.ecosystem',
          label: 'Healthcare ecosystem',
          kind: 'singleton',
          resource: 'about-page',
          description: 'The ecosystem diagram at IIT Kharagpur.',
          fields: [{ name: 'ecosystem_heading', type: 'text', label: 'Heading', max: 80 }, img('ecosystem_image', 'Diagram')],
        },
        {
          id: 'about.timeline',
          label: 'Timeline',
          kind: 'collection',
          resource: 'timeline-entries',
          item_label: ['year', 'title'],
          add_label: 'milestone',
          description: 'Milestones in the centre’s history.',
          fields: [
            { name: 'year', type: 'text', label: 'Year', max: 4, required: true },
            { name: 'title', type: 'text', label: 'Title', max: 80, required: true },
            img('image', 'Photo'),
          ],
        },
        {
          id: 'about.pi-note',
          label: 'Note from the PI',
          kind: 'singleton',
          resource: 'about-page',
          description: 'The Principal Investigator’s note, shown as an image.',
          fields: [img('pi_desk_image', 'Note image')],
        },
        {
          id: 'about.partners',
          label: 'DSIR and IIT Kharagpur',
          kind: 'singleton',
          resource: 'about-page',
          description: 'About the funding department and the institute.',
          fields: [
            { name: 'dsir_about', type: 'richtext', label: 'About DSIR' },
            { name: 'iitkgp_about', type: 'richtext', label: 'About IIT Kharagpur' },
          ],
        },
      ],
    },
    {
      id: 'team',
      path: '/team',
      title: 'Team',
      sections: [
        {
          id: 'team.members',
          label: 'Team members',
          kind: 'collection',
          resource: 'team-members',
          item_label: ['name'],
          add_label: 'team member',
          description: 'Everyone listed on the Team page, grouped by role.',
          fields: [
            img('photo', 'Photo', { help: 'Portrait, shown at 4:5.' }),
            { name: 'name', type: 'text', label: 'Name', max: 80, required: true },
            { name: 'category', type: 'select', label: 'Group', choices_resource: 'team-categories', choice_label: 'name', required: true },
            { name: 'designation', type: 'text', label: 'Designation', max: 80 },
            { name: 'institution', type: 'text', label: 'Institution', max: 120 },
            { name: 'description', type: 'textarea', label: 'Short bio', max: 400 },
          ],
        },
        {
          id: 'team.groups',
          label: 'Groups',
          kind: 'collection',
          resource: 'team-categories',
          item_label: ['name'],
          add_label: 'group',
          description: 'The headings the team is grouped under, in order.',
          fields: [{ name: 'name', type: 'text', label: 'Group name', max: 60, required: true }],
        },
      ],
    },
    {
      id: 'innovations',
      path: '/innovations',
      title: 'Innovations',
      sections: [
        {
          id: 'innovations.spotlight',
          label: 'Project spotlight',
          kind: 'collection',
          resource: 'project-slides',
          item_label: ['title'],
          add_label: 'project slide',
          description: 'The rotating project photos at the top of the page.',
          fields: [img('image', 'Photo', { required: true }), { name: 'title', type: 'text', label: 'Title', max: 60 }],
        },
        {
          id: 'innovations.list',
          label: 'Innovations',
          kind: 'collection',
          resource: 'innovations',
          item_label: ['title'],
          add_label: 'innovation',
          description: 'Each device or technology, with its write-up and photos.',
          fields: [
            { name: 'title', type: 'text', label: 'Title', max: 100, required: true },
            { name: 'body', type: 'richtext', label: 'Write-up' },
            { name: 'video_url', type: 'url', label: 'Video link' },
          ],
          children: [
            {
              resource: 'innovation-images',
              parent_field: 'innovation',
              label: 'Photos',
              item_label: ['caption'],
              add_label: 'photo',
              fields: [img('image', 'Photo', { required: true }), { name: 'caption', type: 'text', label: 'Caption', max: 120 }],
            },
          ],
        },
      ],
    },
    {
      id: 'facilities',
      path: '/facilities',
      title: 'Facilities',
      sections: [
        {
          id: 'facilities.equipment',
          label: 'Lab and testing equipment',
          kind: 'collection',
          resource: 'equipment',
          item_label: ['name'],
          add_label: 'equipment',
          description: 'Equipment available to partners, each with a photo.',
          fields: [{ name: 'name', type: 'text', label: 'Name', max: 100, required: true }, img('image', 'Photo')],
        },
        imageGrid('facilities', 'such as the pilot plant and manufacturing units'),
      ],
    },
    {
      id: 'services',
      path: '/services',
      title: 'Services',
      sections: [
        {
          id: 'services.list',
          label: 'Services',
          kind: 'collection',
          resource: 'services',
          item_label: ['title'],
          add_label: 'service',
          description: 'The services offered to healthcare innovators.',
          fields: [{ name: 'title', type: 'text', label: 'Title', max: 80, required: true }, img('image', 'Photo')],
        },
      ],
    },
    {
      id: 'product',
      path: '/product',
      title: 'Product',
      sections: [
        {
          id: 'product.list',
          label: 'Products',
          kind: 'collection',
          resource: 'products',
          item_label: ['name'],
          add_label: 'product',
          description: 'Products that reached the market, with photos and partners.',
          fields: [{ name: 'name', type: 'text', label: 'Product name', max: 80, required: true }],
          children: [
            {
              resource: 'product-images',
              parent_field: 'product',
              label: 'Photos',
              item_label: [],
              add_label: 'photo',
              fields: [img('image', 'Photo', { required: true })],
            },
            {
              resource: 'product-partners',
              parent_field: 'product',
              label: 'Partners',
              item_label: ['name'],
              add_label: 'partner',
              fields: [{ name: 'name', type: 'text', label: 'Partner name', max: 100, required: true }, img('logo', 'Logo')],
            },
          ],
        },
      ],
    },
    {
      id: 'enterprises',
      path: '/enterprises',
      title: 'Enterprises',
      sections: [
        {
          id: 'enterprises.list',
          label: 'Enterprises',
          kind: 'collection',
          resource: 'enterprises',
          item_label: ['name'],
          add_label: 'enterprise',
          description: 'Enterprises CRTDH has worked with, each with a logo.',
          fields: [
            { name: 'name', type: 'text', label: 'Name', max: 100, required: true },
            { name: 'subtitle', type: 'text', label: 'Subtitle', max: 80, help: 'For example (IIT KGP Spin-off).' },
            img('logo', 'Logo'),
          ],
        },
        imageGrid('enterprises', 'about enterprise engagement'),
        videos('enterprises'),
      ],
    },
    {
      id: 'social-impact',
      path: '/social-impact',
      title: 'Social Impact',
      sections: [imageGrid('social-impact', 'from community camps and clinics'), videos('social-impact')],
    },
    {
      id: 'covid-19',
      path: '/covid-19',
      title: 'Covid-19',
      sections: [imageGrid('covid-19', 'from the pandemic response'), videos('covid-19')],
    },
    {
      id: 'media',
      path: '/media',
      title: 'Media',
      sections: [
        {
          id: 'media.events',
          label: 'Events and camps',
          kind: 'collection',
          resource: 'media-events',
          item_label: ['title'],
          add_label: 'event',
          description: 'Camps, visits and events, each with its photos.',
          fields: [
            { name: 'title', type: 'text', label: 'Title', max: 100, required: true },
            { name: 'event_date', type: 'date', label: 'Date' },
            {
              name: 'category',
              type: 'select',
              label: 'Type',
              choices: [
                { value: '', label: 'Not set' },
                { value: 'camp', label: 'Health camp' },
                { value: 'visit', label: 'Visit' },
                { value: 'workshop', label: 'Workshop' },
                { value: 'event', label: 'Event' },
              ],
            },
            { name: 'description', type: 'textarea', label: 'Description', max: 600 },
          ],
          children: [
            {
              resource: 'media-event-images',
              parent_field: 'event',
              label: 'Photos',
              item_label: ['caption'],
              add_label: 'photo',
              fields: [img('image', 'Photo', { required: true }), { name: 'caption', type: 'text', label: 'Caption', max: 120 }],
            },
          ],
        },
        {
          id: 'media.coverage',
          label: 'Media coverage',
          kind: 'collection',
          resource: 'media-coverage-links',
          item_label: ['title'],
          add_label: 'article',
          description: 'Links to newspaper and web articles about CRTDH.',
          fields: [
            { name: 'title', type: 'text', label: 'Headline', max: 160, required: true },
            { name: 'url', type: 'url', label: 'Article link', required: true },
          ],
        },
        {
          id: 'media.gallery',
          label: 'Gallery',
          kind: 'collection',
          resource: 'gallery-images',
          item_label: ['caption'],
          add_label: 'photo',
          description: 'The photo gallery at the bottom of the Media page.',
          fields: [img('image', 'Photo', { required: true }), { name: 'caption', type: 'text', label: 'Caption', max: 120 }],
        },
        {
          id: 'media.documents',
          label: 'Newsletters and documents',
          kind: 'collection',
          resource: 'documents',
          item_label: ['title'],
          add_label: 'document',
          description: 'Newsletters and forms available to download.',
          fields: [
            { name: 'title', type: 'text', label: 'Title', max: 100, required: true },
            {
              name: 'category',
              type: 'select',
              label: 'Type',
              choices: [
                { value: 'newsletter', label: 'Newsletter' },
                { value: 'membership', label: 'Membership' },
                { value: 'other', label: 'Other' },
              ],
            },
          ],
        },
      ],
    },
    {
      id: 'contact',
      path: '/contact',
      title: 'Contact',
      sections: [
        {
          id: 'contact.details',
          label: 'Office details',
          kind: 'singleton',
          resource: 'site-settings',
          description: 'Address, phone numbers, email and map. Also used in the footer.',
          fields: [
            { name: 'address', type: 'textarea', label: 'Address', max: 300 },
            { name: 'phone_primary', type: 'text', label: 'Phone', max: 30 },
            { name: 'phone_secondary', type: 'text', label: 'Second phone', max: 30 },
            { name: 'email_primary', type: 'text', label: 'Email', max: 120 },
            { name: 'email_secondary', type: 'text', label: 'Second email', max: 120 },
            { name: 'map_embed_url', type: 'url', label: 'Google Maps embed link', help: 'From Google Maps: Share › Embed a map › copy the src link.' },
          ],
        },
      ],
    },
    {
      id: 'site',
      path: null,
      title: 'Header & footer',
      sections: [
        {
          id: 'site.nav',
          label: 'Menu links',
          kind: 'collection',
          resource: 'nav-items',
          item_label: ['label'],
          add_label: 'menu link',
          description: 'The links in the top menu, in order.',
          fields: [
            { name: 'label', type: 'text', label: 'Link text', max: 30, required: true },
            { name: 'url', type: 'url', label: 'Goes to', required: true },
            { name: 'in_more', type: 'boolean', label: 'Put under “More”', help: 'Keeps the main menu short.' },
          ],
        },
        {
          id: 'site.social',
          label: 'Social links',
          kind: 'singleton',
          resource: 'site-settings',
          description: 'Social media links in the footer. Leave empty to hide an icon.',
          fields: [
            { name: 'facebook_url', type: 'url', label: 'Facebook' },
            { name: 'linkedin_url', type: 'url', label: 'LinkedIn' },
            { name: 'instagram_url', type: 'url', label: 'Instagram' },
            { name: 'twitter_url', type: 'url', label: 'X (Twitter)' },
          ],
        },
        {
          id: 'site.logos',
          label: 'Logos',
          kind: 'singleton',
          resource: 'site-settings',
          description: 'The site logo and the partner logos in the header.',
          fields: [img('site_logo', 'Site logo'), img('logo_left', 'Left partner logo'), img('logo_right', 'Right partner logo')],
        },
      ],
    },
  ],
};

export const SINGLETON_RESOURCES = ['site-settings', 'about-page', 'home-page'];
