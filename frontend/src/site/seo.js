// Titles and descriptions per page (from the existing site copy). `image` picks the page's OG image.
const first = (rows, key = 'image') => (rows || []).find((r) => r && r[key])?.[key]
const T = (s) => `${s} · CRTDH, IIT Kharagpur`

export const SEO = {
  home: {
    path: '/',
    title: 'CRTDH · Affordable healthcare technology at IIT Kharagpur',
    description:
      'Common Research and Technology Development Hub on Affordable Healthcare: a DSIR-sponsored centre at IIT Kharagpur developing low-cost diagnostics and medical devices with MSMEs and startups.',
  },
  about: { path: '/about/', title: T('About'), description: 'A DSIR-sponsored initiative at IIT Kharagpur translating research in basic sciences, sensors and digital health into affordable, deployable healthcare technology.', image: (d) => d.singletons?.['about-page']?.ecosystem_image },
  team: { path: '/team/', title: T('Team'), description: 'The people behind CRTDH: principal investigators, project staff and medical collaborators.', image: (d) => first(d.collections?.['team-members'], 'photo') },
  innovations: { path: '/innovations/', title: T('Innovations'), description: 'CRTDH-developed medical devices, diagnostics and digital health tools, built for low-resource settings.', image: (d) => first(d.collections?.['project-slides']) },
  facilities: { path: '/facilities/', title: T('Facilities'), description: 'Instrumentation, pilot manufacturing and sterile facilities available to CRTDH researchers and partner enterprises.', image: (d) => first(d.collections?.equipment) },
  services: { path: '/services/', title: T('Services'), description: 'R&D support, prototyping and testing, regulatory guidance, training and market access for healthcare MSMEs and startups.', image: (d) => first(d.collections?.services) },
  product: { path: '/product/', title: T('Products'), description: 'Products developed under CRTDH and the partners commercialising them.', image: (d) => first((d.collections?.products || []).flatMap((p) => p.images || [])) },
  enterprises: { path: '/enterprises/', title: T('Enterprises'), description: 'MSMEs and startups engaged with CRTDH, from medtech startups scaling manufacturing to rural livelihood ventures.', image: (d) => d.singletons?.['home-page']?.enterprises_image_1 },
  'social-impact': { path: '/social-impact/', title: T('Social impact'), description: 'Health camps, rural e-clinics and outreach programmes bringing CRTDH innovations to the people who need them most.', image: (d) => d.singletons?.['home-page']?.women_image_1 },
  'covid-19': { path: '/covid-19/', title: T('Covid-19 response'), description: 'Diagnostics, training and community relief undertaken by CRTDH during the Covid-19 pandemic, including the PINAT test platform.' },
  media: { path: '/media/', title: T('Media and gallery'), description: 'Photographs from CRTDH events, health camps and outreach programmes, press coverage and newsletters.', image: (d) => first((d.collections?.['media-events'] || []).flatMap((e) => e.images || [])) },
  contact: { path: '/contact/', title: T('Contact'), description: 'Write to CRTDH, IIT Kharagpur about research, facilities, services or working with the centre.' },
  notfound: { path: '/404/', title: T('Page not found'), description: 'This page does not exist on the CRTDH website.' },
}
