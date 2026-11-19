// Renders the real public page for the canvas. `@site` is the frontend
// lane's `frontend/src/site` package (page components `({ data }) => JSX`,
// exported as `pages` keyed by registry page id, plus an optional `Layout`).
// Until that package exists the Vite alias points at ./site-shim.
//
// Clickable sections: each section root carries `data-cms-section="<section id>"`
// (and collection items `data-cms-item="<pk>"`). The canvas adds outlines and
// selection around those attributes; nothing editor-specific is needed in the
// public components beyond them.
import { Fragment } from 'react';
import * as site from '@site';

export const usingShim = !!site.__shim;

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
