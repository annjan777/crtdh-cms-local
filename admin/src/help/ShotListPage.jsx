// Plan WS2.6: the photo shot list linked from rejected or small uploads.
import AppShell, { PageNav } from '../shell/AppShell.jsx';

const SHOTS = [
  ['Building exteriors', 'The Bioscience Building and the Diamond Jubilee Complex in daylight, landscape.'],
  ['Labs at work', 'People using the prototyping, testing and validation labs; faces lit, hands visible.'],
  ['Devices in use', 'Each device in a clinic or camp setting, held or in use, not on a plain table.'],
  ['Health camps', 'Wide shots of camps showing the community and the team, plus close-ups of screening.'],
  ['Team', 'Portraits against a plain wall, chest up, in portrait orientation (4:5).'],
];

export default function ShotListPage() {
  return (
    <AppShell crumb="Photo shot list">
      {/* On phones this scroll area holds no link or field, so it must be focusable to scroll by keyboard. */}
      <div className="editor is-wide page-layout" tabIndex={0} role="region" aria-label="Photo shot list">
        <div className="col-nav">
          <PageNav />
        </div>
        <main id="main" className="page-main" tabIndex={-1}>
          <header className="page-head">
            <h1>Photo shot list</h1>
            <p className="lead">Large, sharp photos make the site. Hero photos must be at least 1600 px wide (2400 px is better); photos elsewhere should be 1200 px or more. Phone cameras are fine: send the original file, not a WhatsApp copy, which is shrunk.</p>
          </header>
          <div className="table-frame">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Subject</th>
                  <th scope="col">What to capture</th>
                </tr>
              </thead>
              <tbody>
                {SHOTS.map(([a, b]) => (
                  <tr key={a}>
                    <td className="cell-main">{a}</td>
                    <td>{b}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </main>
      </div>
    </AppShell>
  );
}
