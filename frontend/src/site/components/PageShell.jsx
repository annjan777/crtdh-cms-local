import { MediaProvider } from '../media.jsx'

export default function PageShell({ data, className = '', children }) {
  return (
    <MediaProvider media={data?.media}>
      <div className={`page ${className}`}>{children}</div>
    </MediaProvider>
  )
}
