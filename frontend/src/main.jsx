import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { MotionConfig } from 'framer-motion'
import '@fontsource-variable/fraunces/standard.css'
import '@fontsource-variable/fraunces/standard-italic.css'
import '@fontsource/public-sans/400.css'
import '@fontsource/public-sans/500.css'
import '@fontsource/public-sans/600.css'
import '@fontsource/public-sans/700.css'
import '@fontsource/public-sans/800.css'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      {/* Follow the OS "reduce motion" setting for every Framer Motion animation (transforms off, fades kept). */}
      <MotionConfig reducedMotion="user">
        <App />
      </MotionConfig>
    </BrowserRouter>
  </StrictMode>,
)
