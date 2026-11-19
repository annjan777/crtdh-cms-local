// Renders the real public page for the canvas. `@site` is the frontend
// lane's `frontend/src/site` package (page components `({ data }) => JSX`,
// exported as `pages` keyed by registry page id, plus an optional `Layout`).
//
// Clickable sections: the public components carry no editor markup, so the canvas
// tags their blocks with `data-cms-section` (and `data-cms-item` where the markup
// names the row) from src/preview/section-map.js after each render.
import { Fragment } from 'react';
import * as site from '@site';

export default function SitePreview({ pageId, data }) {
  const pages = site.pages || {};
  const Page = pages[pageId] || (pageId === 'site' ? pages.home : null);
  const Layout = site.Layout || Fragment;
  if (!Page)
    return (
      <div style={{ padding: 40, font: '16px/1.5 system-ui' }}>
        <p>The public site has no component for the page “{pageId}” yet.</p>
      </div>
    );
  return (
    <Layout data={data} pageId={pageId}>
      <Page data={data} />
    </Layout>
  );
}
