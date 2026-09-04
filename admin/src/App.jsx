import { Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import SiteSettingsPage from './pages/SiteSettingsPage';
import AboutPageAdmin from './pages/AboutPageAdmin';
import HomePageSectionsEditor from './pages/HomePageSectionsEditor';
import HeroCarouselManager from './components/HeroCarouselManager';
import TeamManager from './components/TeamManager';
import MediaGalleryManager from './components/MediaGalleryManager';
import CentralMediaLibrary from './components/CentralMediaLibrary';
import ContactMessagesPage from './pages/ContactMessagesPage';
import NavbarMenuLinksManager from './pages/NavbarMenuLinksManager';
import ResourceListPage from './pages/ResourceListPage';
import ResourceFormPage from './pages/ResourceFormPage';
import NotFoundPage from './pages/NotFoundPage';

export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route index element={<DashboardPage />} />
              <Route path="site-settings" element={<SiteSettingsPage />} />
              <Route path="home-page" element={<HomePageSectionsEditor />} />
              <Route path="about-page" element={<AboutPageAdmin />} />
              <Route path="hero-manager" element={<HeroCarouselManager />} />
              <Route path="team-manager" element={<TeamManager />} />
              <Route path="media-gallery" element={<MediaGalleryManager />} />
              <Route path="media-library" element={<CentralMediaLibrary />} />
              <Route path="contact-messages" element={<ContactMessagesPage />} />
              <Route path="resources/nav-items" element={<NavbarMenuLinksManager />} />
              <Route path="resources/:resourceKey" element={<ResourceListPage />} />
              <Route path="resources/:resourceKey/new" element={<ResourceFormPage />} />
              <Route path="resources/:resourceKey/:id" element={<ResourceFormPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </ToastProvider>
  );
}
