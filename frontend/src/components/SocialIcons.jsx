// lucide-react dropped brand/logo icons a while back, so the handful of
// social marks we still need (footer social links) are small hand-rolled
// SVGs in the same 16/24 stroke-friendly style as the rest of the icon set.

export function FacebookIcon({ size = '1em', ...props }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" width={size} height={size} {...props}>
      <path d="M13.5 21v-7.5h2.5l.4-3H13.5V8.4c0-.87.24-1.46 1.49-1.46H16.5V4.34C16.2 4.3 15.2 4.2 14 4.2c-2.4 0-4 1.47-4 4.16V10.5H7.5v3H10V21h3.5Z" />
    </svg>
  )
}

export function InstagramIcon({ size = '1em', ...props }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width={size} height={size} {...props}>
      <rect x="3.5" y="3.5" width="17" height="17" rx="4.5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.2" cy="6.8" r="1" fill="currentColor" stroke="none" />
    </svg>
  )
}

export function LinkedinIcon({ size = '1em', ...props }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" width={size} height={size} {...props}>
      <path d="M6.94 8.5H4.06V20h2.88V8.5ZM5.5 4a1.7 1.7 0 1 0 0 3.4A1.7 1.7 0 0 0 5.5 4ZM20 13.3c0-3-1.6-4.4-3.75-4.4-1.73 0-2.5.95-2.94 1.62V8.5H10.5c.04.83 0 11.5 0 11.5h2.81v-6.42c0-.34.02-.69.13-.94.28-.68.9-1.4 1.96-1.4 1.38 0 1.93 1.05 1.93 2.6V20H20v-6.7Z" />
    </svg>
  )
}

export function TwitterIcon({ size = '1em', ...props }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" width={size} height={size} {...props}>
      <path d="M18.9 4h2.9l-6.34 7.25L23 20h-5.84l-4.58-6-5.24 6H4.44l6.78-7.75L4 4h5.98l4.14 5.48L18.9 4Zm-1.02 14.4h1.6L8.2 5.52H6.48L17.88 18.4Z" />
    </svg>
  )
}
