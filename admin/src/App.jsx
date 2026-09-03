import { Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import SiteSettingsPage from './pages/SiteSettingsPage';
import AboutPageAdmin from './pages/AboutPageAdmin';
import HomePageAdmin from './pages/HomePageAdmin';
import ContactMessagesPage from './pages/ContactMessagesPage';
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
              <Route path="home-page" element={<HomePageAdmin />} />
              <Route path="about-page" element={<AboutPageAdmin />} />
              <Route path="contact-messages" element={<ContactMessagesPage />} />
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
