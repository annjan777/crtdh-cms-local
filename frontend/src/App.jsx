import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import About from './pages/About'
import Team from './pages/Team'
import Innovations from './pages/Innovations'
import Facilities from './pages/Facilities'
import Services from './pages/Services'
import Enterprises from './pages/Enterprises'
import Product from './pages/Product'
import SocialImpact from './pages/SocialImpact'
import Covid19 from './pages/Covid19'
import Media from './pages/Media'
import Contact from './pages/Contact'
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/about" element={<About />} />
        <Route path="/team" element={<Team />} />
        <Route path="/innovations" element={<Innovations />} />
        <Route path="/facilities" element={<Facilities />} />
        <Route path="/services" element={<Services />} />
        <Route path="/enterprises" element={<Enterprises />} />
        <Route path="/product" element={<Product />} />
        <Route path="/social-impact" element={<SocialImpact />} />
        <Route path="/covid-19" element={<Covid19 />} />
        <Route path="/media" element={<Media />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
