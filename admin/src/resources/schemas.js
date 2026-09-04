// Config-driven CRUD schema for every resource in API_CONTRACT.md.
//
// Each entry describes one top-level DRF resource: its endpoint, its form
// fields (with a `type` the generic form/list renderers know how to
// display), whether it supports drag-reorder, and — for parents with
// nested children per the contract — the child resources that should be
// managed inline on the parent's edit screen instead of only through their
// own top-level endpoint.
//
// Field types understood by <FormField>/<ResourceCrudPage>:
//   text | textarea | richtext | number | select | image | file
//
// `select` fields take either a static `options: [{value, label}]` array
// (enums, e.g. Document.category) or `optionsEndpoint` + `optionLabel` to
// populate the dropdown from another resource (FK pickers, e.g.
// TeamMember.category).
//
// To add a new resource once the backend adds one: add one object to
// RESOURCE_SCHEMAS (or one entry to a `children` array for a nested type).
// Nothing else in the app needs to change — the dashboard, sidebar nav,
// list view, create/edit form, image upload, and reorder all read this
// config. See admin/README.md for a worked example.

export const RESOURCE_SCHEMAS = [
  // ---- Global -----------------------------------------------------------
  {
    key: 'nav-items',
    label: 'Nav Items',
    group: 'Global',
    icon: 'link-2',
    endpoint: '/nav-items/',
    orderable: true,
    fields: [
      { name: 'label', label: 'Label', type: 'text', required: true },
      { name: 'url', label: 'URL', type: 'text', required: true },
    ],
    listColumns: ['label', 'url'],
  },
  {
    key: 'news-items',
    label: 'News Items',
    group: 'Global',
    icon: 'megaphone',
    endpoint: '/news-items/',
    orderable: true,
    fields: [
      { name: 'text', label: 'Text', type: 'textarea', required: true },
      { name: 'link_url', label: 'Link URL', type: 'text' },
    ],
    listColumns: ['text', 'link_url'],
  },

  // ---- Carousels ----------------------------------------------------------
  {
    key: 'hero-slides',
    label: 'Hero Slides',
    group: 'Carousels',
    icon: 'gallery-horizontal',
    endpoint: '/hero-slides/',
    orderable: true,
    fields: [{ name: 'image', label: 'Image', type: 'image', required: true }],
    listColumns: ['image'],
  },
  {
    key: 'project-slides',
    label: 'Project Slides',
    group: 'Carousels',
    icon: 'presentation',
    endpoint: '/project-slides/',
    orderable: true,
    fields: [
      { name: 'image', label: 'Image', type: 'image', required: true },
      { name: 'title', label: 'Title', type: 'text' },
    ],
    listColumns: ['image', 'title'],
  },

  // ---- Team ---------------------------------------------------------------
  {
    key: 'team-categories',
    label: 'Team Categories',
    group: 'Team',
    icon: 'folder-tree',
    endpoint: '/team-categories/',
    orderable: true,
    fields: [{ name: 'name', label: 'Name', type: 'text', required: true }],
    listColumns: ['name'],
  },
  {
    key: 'team-members',
    label: 'Team Members',
    group: 'Team',
    icon: 'users',
    endpoint: '/team-members/',
    orderable: true,
    fields: [
      {
        name: 'category',
        label: 'Category',
        type: 'select',
        required: true,
        optionsEndpoint: '/team-categories/',
        optionLabel: 'name',
      },
      { name: 'name', label: 'Name', type: 'text', required: true },
      { name: 'photo', label: 'Photo', type: 'image' },
    ],
    listColumns: ['photo', 'name', 'category_name'],
  },

  // ---- Facilities -----------------------------------------------------------
  {
    key: 'equipment',
    label: 'Equipment',
    group: 'Facilities',
    icon: 'wrench',
    endpoint: '/equipment/',
    orderable: true,
    fields: [
      { name: 'name', label: 'Name', type: 'text', required: true },
      { name: 'image', label: 'Image', type: 'image' },
    ],
    listColumns: ['image', 'name'],
  },

  // ---- Services -------------------------------------------------------------
  {
    key: 'services',
    label: 'Services',
    group: 'Services',
    icon: 'briefcase',
    endpoint: '/services/',
    orderable: true,
    fields: [
      { name: 'title', label: 'Title', type: 'text', required: true },
      { name: 'image', label: 'Image', type: 'image' },
    ],
    listColumns: ['image', 'title'],
  },

  // ---- Innovations ----------------------------------------------------------
  {
    key: 'innovations',
    label: 'Innovations',
    group: 'Innovations',
    icon: 'lightbulb',
    endpoint: '/innovations/',
    orderable: true,
    fields: [
      { name: 'title', label: 'Title', type: 'text', required: true },
      { name: 'body', label: 'Body', type: 'richtext' },
      { name: 'video_url', label: 'Video URL', type: 'text' },
    ],
    listColumns: ['title', 'video_url'],
    children: [
      {
        key: 'images',
        label: 'Images',
        endpoint: '/innovation-images/',
        parentField: 'innovation',
        nestedField: 'images',
        orderable: true,
        fields: [
          { name: 'image', label: 'Image', type: 'image', required: true },
          { name: 'caption', label: 'Caption', type: 'text' },
        ],
      },
    ],
  },

  // ---- Products ---------------------------------------------------------------
  {
    key: 'products',
    label: 'Products',
    group: 'Products',
    icon: 'package',
    endpoint: '/products/',
    orderable: true,
    fields: [{ name: 'name', label: 'Name', type: 'text', required: true }],
    listColumns: ['name'],
    children: [
      {
        key: 'images',
        label: 'Images',
        endpoint: '/product-images/',
        parentField: 'product',
        nestedField: 'images',
        orderable: true,
        fields: [{ name: 'image', label: 'Image', type: 'image', required: true }],
      },
      {
        key: 'partners',
        label: 'Partners',
        endpoint: '/product-partners/',
        parentField: 'product',
        nestedField: 'partners',
        orderable: false,
        fields: [
          { name: 'name', label: 'Name', type: 'text', required: true },
          { name: 'logo', label: 'Logo', type: 'image' },
        ],
      },
    ],
  },

  // ---- Enterprises ----------------------------------------------------------
  {
    key: 'enterprises',
    label: 'Enterprises',
    group: 'Enterprises',
    icon: 'building',
    endpoint: '/enterprises/',
    orderable: true,
    fields: [
      { name: 'name', label: 'Name', type: 'text', required: true },
      { name: 'subtitle', label: 'Subtitle', type: 'text' },
      { name: 'logo', label: 'Logo', type: 'image' },
    ],
    listColumns: ['logo', 'name', 'subtitle'],
  },

  // ---- Media / gallery --------------------------------------------------------
  {
    key: 'media-events',
    label: 'Media Events',
    group: 'Media',
    icon: 'calendar',
    endpoint: '/media-events/',
    orderable: true,
    fields: [
      { name: 'title', label: 'Title', type: 'text', required: true },
      { name: 'slug', label: 'Slug', type: 'text', required: true },
    ],
    listColumns: ['title', 'slug'],
    children: [
      {
        key: 'images',
        label: 'Images',
        endpoint: '/media-event-images/',
        parentField: 'event',
        nestedField: 'images',
        orderable: true,
        fields: [
          { name: 'image', label: 'Image', type: 'image', required: true },
          { name: 'caption', label: 'Caption', type: 'text' },
        ],
      },
    ],
  },
  {
    key: 'media-coverage-links',
    label: 'Media Coverage Links',
    group: 'Media',
    icon: 'newspaper',
    endpoint: '/media-coverage-links/',
    orderable: true,
    fields: [
      { name: 'title', label: 'Title', type: 'text', required: true },
      { name: 'url', label: 'URL', type: 'text', required: true },
    ],
    listColumns: ['title', 'url'],
  },
  {
    key: 'gallery-images',
    label: 'Gallery Images',
    group: 'Media',
    icon: 'images',
    endpoint: '/gallery-images/',
    orderable: true,
    fields: [
      { name: 'image', label: 'Image', type: 'image', required: true },
      { name: 'caption', label: 'Caption', type: 'text' },
    ],
    listColumns: ['image', 'caption'],
  },

  // ---- Generic image grids ------------------------------------------------
  {
    key: 'image-grid-blocks',
    label: 'Image Grid Blocks',
    group: 'Image Grids',
    icon: 'layout-grid',
    endpoint: '/image-grid-blocks/',
    orderable: true,
    fields: [
      {
        name: 'page',
        label: 'Page',
        type: 'text',
        required: true,
        hint: 'e.g. "facilities", "services", "enterprises", "social-impact", "covid-19", "home"',
      },
      { name: 'section_title', label: 'Section Title', type: 'text' },
      { name: 'anchor_slug', label: 'Anchor Slug', type: 'text' },
    ],
    listColumns: ['page', 'section_title', 'anchor_slug'],
    children: [
      {
        key: 'items',
        label: 'Items',
        endpoint: '/image-grid-items/',
        parentField: 'block',
        nestedField: 'items',
        orderable: true,
        fields: [
          { name: 'image', label: 'Image', type: 'image', required: true },
          { name: 'caption', label: 'Caption', type: 'text' },
        ],
      },
    ],
  },

  // ---- Video blocks -----------------------------------------------------------
  {
    key: 'video-blocks',
    label: 'Video Blocks',
    group: 'Video',
    icon: 'video',
    endpoint: '/video-blocks/',
    orderable: true,
    fields: [
      { name: 'title', label: 'Title', type: 'text', required: true },
      { name: 'page', label: 'Page', type: 'text', required: true },
      { name: 'youtube_url', label: 'YouTube URL', type: 'text' },
      { name: 'video_file', label: 'Video File', type: 'file' },
    ],
    listColumns: ['title', 'page', 'youtube_url'],
  },

  // ---- Documents ----------------------------------------------------------------
  {
    key: 'documents',
    label: 'Documents',
    group: 'Documents',
    icon: 'file',
    endpoint: '/documents/',
    orderable: true,
    fields: [
      { name: 'title', label: 'Title', type: 'text', required: true },
      { name: 'file', label: 'File', type: 'file', required: true },
      {
        name: 'category',
        label: 'Category',
        type: 'select',
        required: true,
        options: [
          { value: 'newsletter', label: 'Newsletter' },
          { value: 'membership', label: 'Membership' },
          { value: 'other', label: 'Other' },
        ],
      },
    ],
    listColumns: ['title', 'category'],
  },

  // ---- About page ---------------------------------------------------------------
  {
    key: 'focus-areas',
    label: 'Focus Areas',
    group: 'About Page',
    icon: 'target',
    endpoint: '/focus-areas/',
    orderable: true,
    fields: [
      { name: 'title', label: 'Title', type: 'text', required: true },
      { name: 'color', label: 'Color', type: 'text', hint: 'e.g. a hex code like #1e3a8a' },
    ],
    listColumns: ['title', 'color'],
  },
  {
    key: 'objective-rows',
    label: 'Objective Rows',
    group: 'About Page',
    icon: 'list-checks',
    endpoint: '/objective-rows/',
    orderable: true,
    fields: [
      { name: 'category', label: 'Category', type: 'text', hint: 'Groups rows under a shared row header, e.g. "Ideation"' },
      { name: 'task', label: 'Task', type: 'textarea', required: true },
      { name: 'outcome', label: 'Outcome', type: 'textarea' },
    ],
    listColumns: ['category', 'task', 'outcome'],
  },
  {
    key: 'timeline-entries',
    label: 'Timeline Entries',
    group: 'About Page',
    icon: 'history',
    endpoint: '/timeline-entries/',
    orderable: true,
    fields: [
      { name: 'year', label: 'Year', type: 'text', required: true },
      { name: 'title', label: 'Title', type: 'text', required: true },
      { name: 'image', label: 'Image', type: 'image' },
    ],
    listColumns: ['image', 'year', 'title'],
  },
];

export function getResourceSchema(key) {
  return RESOURCE_SCHEMAS.find((r) => r.key === key) || null;
}

// Icon (see resources/icons.js) shown next to each group's label in the
// sidebar and on the dashboard's section headings.
export const GROUP_ICONS = {
  Global: 'globe',
  Carousels: 'gallery-horizontal',
  Team: 'users',
  Facilities: 'wrench',
  Services: 'briefcase',
  Innovations: 'lightbulb',
  Products: 'package',
  Enterprises: 'building',
  Media: 'image',
  'Image Grids': 'layout-grid',
  Video: 'video',
  Documents: 'file',
  'About Page': 'info',
};

// Grouped for the sidebar/dashboard nav, in a sensible reading order.
export function groupedSchemas() {
  const order = [
    'Global',
    'Carousels',
    'Team',
    'Facilities',
    'Services',
    'Innovations',
    'Products',
    'Enterprises',
    'Media',
    'Image Grids',
    'Video',
    'Documents',
    'About Page',
  ];
  const groups = new Map();
  for (const schema of RESOURCE_SCHEMAS) {
    if (!groups.has(schema.group)) groups.set(schema.group, []);
    groups.get(schema.group).push(schema);
  }
  return order
    .filter((g) => groups.has(g))
    .map((g) => ({ group: g, icon: GROUP_ICONS[g] || 'boxes', items: groups.get(g) }));
}
