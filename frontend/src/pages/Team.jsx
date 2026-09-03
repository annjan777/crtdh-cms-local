import { User } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { fetchList } from '../api/client'
import PageHero from '../components/PageHero'
import { DataState, Spinner } from '../components/StateBlock'
import Reveal, { Stagger, StaggerItem } from '../components/Reveal'
import TiltCard from '../components/TiltCard'
import './Team.css'

export default function Team() {
  const { data: categories, loading: catLoading, error: catError } = useApi(
    () => fetchList('/team-categories/'),
    [],
    [],
  )
  const { data: members, loading: memberLoading } = useApi(() => fetchList('/team-members/'), [], [])

  const loading = catLoading || memberLoading

  return (
    <div>
      <PageHero
        eyebrow="Team"
        title="PI, Co-PIs and Research Team"
        description="The people behind CRTDH — principal investigators, project staff and medical collaborators."
      />

      <section className="section">
        <div className="container">
          {loading ? (
            <Spinner />
          ) : (
            <DataState
              loading={false}
              error={catError}
              data={categories}
              emptyProps={{ title: 'Team members coming soon' }}
            >
              {(cats) => (
                <div className="team-categories">
                  {cats.map((category, catIndex) => {
                    const categoryMembers = (members || []).filter((m) => m.category === category.id)
                    return (
                      <div className="team-category" key={category.id}>
                        <Reveal as="h2" className="team-category__title" delay={Math.min(catIndex, 3) * 0.05}>
                          {category.name}
                        </Reveal>
                        {categoryMembers.length === 0 ? (
                          <p className="team-category__empty">No members listed yet.</p>
                        ) : (
                          <Stagger className="grid grid--4">
                            {categoryMembers.map((member) => (
                              <StaggerItem key={member.id}>
                                <TiltCard max={7}>
                                  <div className="team-card card">
                                    <div className="team-card__photo">
                                      {member.photo ? (
                                        <img src={member.photo} alt={member.name} loading="lazy" />
                                      ) : (
                                        <User size={28} aria-hidden="true" />
                                      )}
                                    </div>
                                    <p className="team-card__name">{member.name}</p>
                                  </div>
                                </TiltCard>
                              </StaggerItem>
                            ))}
                          </Stagger>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </DataState>
          )}
        </div>
      </section>
    </div>
  )
}
