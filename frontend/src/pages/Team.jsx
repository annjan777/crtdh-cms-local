import { User, Users, Settings, Users2, ArrowRight, Mail } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import { DataState, Spinner } from '../components/StateBlock'
import Reveal, { Stagger, StaggerItem } from '../components/Reveal'
import TiltCard from '../components/TiltCard'
import './Team.css'

// Badge text: the member's own designation if set, otherwise a label for their group.
function badgeFor(member, categoryName) {
  if (member.designation) return member.designation
  const n = (categoryName || '').toLowerCase()
  if (n.includes('co-principal')) return 'Co-Principal Investigator'
  if (n.includes('principal')) return 'Principal Investigator'
  if (n.includes('other')) return 'Research Member'
  return categoryName
}

function getCategoryMeta(name) {
  const n = (name || '').toLowerCase()
  if (n.includes('principal investigator') && !n.includes('co-')) {
    return {
      icon: User,
      layout: 'featured',
      desc: "Providing leadership and strategic direction to CRTDH's research, innovation and technology development initiatives.",
    }
  }
  if (n.includes('co-principal')) {
    return {
      icon: Users,
      layout: 'grid-3',
      desc: 'Supporting CRTDH through their expertise across research, development and collaboration.',
    }
  }
  if (n.includes('other')) {
    return {
      icon: Users,
      layout: 'grid-2',
      desc: "Researchers and collaborators contributing to CRTDH's mission.",
    }
  }
  if (n.includes('manager')) {
    return {
      icon: Settings,
      layout: 'featured',
      desc: 'Coordinating project activities and ensuring effective execution.',
    }
  }
  if (n.includes('staff')) {
    return {
      icon: Users2,
      layout: 'grid-4',
      desc: 'Dedicated staff members supporting research, development and day-to-day operations.',
    }
  }
  return {
    icon: Users,
    layout: 'grid-4',
    desc: 'Team members contributing to the success of CRTDH.',
  }
}

export default function Team() {
  const { data: categories, loading: catLoading, error: catError } = useApi(() => fetchList('/team-categories/'), [], [])
  const { data: members, loading: memberLoading } = useApi(() => fetchList('/team-members/'), [], [])
  const { data: slides } = useApi(() => fetchList('/hero-slides/'), [], [])

  const loading = catLoading || memberLoading
  const bannerSlide = (slides || []).find((s) => s.is_published !== false)

  return (
    <div className="team-page bg-page">
      <PageHero
        eyebrow="Team"
        title="PI, Co-PIs and Research Team"
        description="The people behind CRTDH — principal investigators, project staff and medical collaborators."
        image={bannerSlide?.image}
        imagePosition={bannerSlide?.image_position}
      />

      <section className="section team-main">
        <div className="container">
          {loading ? (
            <Spinner />
          ) : (
            <DataState loading={false} error={catError} data={categories} emptyProps={{ title: 'Team members coming soon' }}>
              {(cats) => (
                <div className="team-sections">
                  {cats.map((category, catIndex) => {
                    const categoryMembers = (members || []).filter(
                      (m) => m.category === category.id && m.is_published !== false,
                    )
                    if (categoryMembers.length === 0) return null

                    const meta = getCategoryMeta(category.name)
                    const Icon = meta.icon

                    return (
                      <Reveal key={category.id} className="team-section-wrap" delay={0.05 * catIndex}>
                        <div className="team-section">
                          <div className="team-section__sidebar">
                            <div className="team-section__icon">
                              <Icon size={24} aria-hidden="true" />
                            </div>
                            <h2>{category.name}</h2>
                            <p>{meta.desc}</p>
                          </div>
                          
                          <div className="team-section__content">
                            {meta.layout === 'featured' && categoryMembers.length === 1 ? (
                              <div className="team-featured-card card shadow-sm">
                                <div className="team-featured__photo">
                                  {categoryMembers[0].photo ? (
                                    <img src={categoryMembers[0].photo} alt={categoryMembers[0].name} loading="lazy" />
                                  ) : (
                                    <User size={40} aria-hidden="true" />
                                  )}
                                </div>
                                <div className="team-featured__info">
                                  <div className="team-featured__header">
                                    <h3>{categoryMembers[0].name}</h3>
                                    <span className="team-badge">{badgeFor(categoryMembers[0], category.name)}</span>
                                  </div>
                                  {categoryMembers[0].institution && (
                                    <p className="team-institution">{categoryMembers[0].institution}</p>
                                  )}
                                  {categoryMembers[0].email && (
                                    <div className="team-featured__extra">
                                      <Mail size={16} /> <span>{categoryMembers[0].email}</span>
                                    </div>
                                  )}
                                  {(categoryMembers[0].description || /principal/i.test(category.name)) && (
                                    <div className="team-featured__desc">
                                      {categoryMembers[0].description ? (
                                        <p>{categoryMembers[0].description}</p>
                                      ) : (
                                        <>
                                          <h4>Research Leadership</h4>
                                          <p>Guiding CRTDH's vision for affordable healthcare technologies.</p>
                                        </>
                                      )}
                                    </div>
                                  )}
                                </div>
                              </div>
                            ) : (
                              <Stagger className={`grid team-grid team-grid--${meta.layout}`}>
                                {categoryMembers.map((member) => (
                                  <StaggerItem key={member.id} className="team-card-wrap">
                                    <TiltCard max={4} className="h-100">
                                      <div className="team-card card shadow-sm h-100">
                                        <div className="team-card__photo">
                                          {member.photo ? (
                                            <img src={member.photo} alt={member.name} loading="lazy" />
                                          ) : (
                                            <User size={28} aria-hidden="true" />
                                          )}
                                        </div>
                                        <div className="team-card__info">
                                          <h3 className="team-card__name">{member.name}</h3>
                                          <span className="team-badge">{badgeFor(member, category.name)}</span>
                                          {member.institution && <p className="team-card__inst">{member.institution}</p>}
                                          {member.description && <p className="team-card__desc">{member.description}</p>}
                                        </div>
                                      </div>
                                    </TiltCard>
                                  </StaggerItem>
                                ))}
                              </Stagger>
                            )}
                          </div>
                        </div>
                      </Reveal>
                    )
                  })}
                </div>
              )}
            </DataState>
          )}
        </div>
      </section>

      <section className="section team-cta-section">
        <div className="container">
          <Reveal className="team-cta card">
            <div className="team-cta__left">
              <div className="team-cta__icon"><Users size={32} /></div>
              <div>
                <h2>A multidisciplinary team working towards<br/>innovative healthcare solutions</h2>
                <p>Research. Innovation. Collaboration. Impact.</p>
              </div>
            </div>
            <div className="team-cta__right">
              <Link to="/contact" className="btn btn--primary">
                Get in Touch <ArrowRight size={17} />
              </Link>
            </div>
          </Reveal>
        </div>
      </section>
    </div>
  )
}
