import { createContext, useContext } from 'react';

// Editor-only context for the preview iframe. Public page components may read
// it (for example to show the slide being edited) but must render the same
// without it; it is never provided in the public build.
//   sections: registry sections of the open page (id, label, kind, resource, fields, filter)
//   selected: { sectionId, pk } or null
export const CmsPreviewContext = createContext({ sections: [], selected: null, pageId: null });
export const useCmsPreview = () => useContext(CmsPreviewContext);
