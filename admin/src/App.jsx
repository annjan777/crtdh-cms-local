import { Navigate, Outlet, createBrowserRouter } from 'react-router-dom';
import { useAuth } from './auth/AuthContext.jsx';
import AuthScreens from './auth/AuthScreens.jsx';
import { ChangesProvider } from './shell/ChangesContext.jsx';
import EditorPage from './editor/EditorPage.jsx';
import ReviewPage from './review/ReviewPage.jsx';
import HistoryPage from './history/HistoryPage.jsx';
import UsersPage from './users/UsersPage.jsx';
import ShotListPage from './help/ShotListPage.jsx';

function Gate() {
  const { status } = useAuth();
  if (status === 'loading')
    return (
      <div className="app" aria-busy="true">
        <header className="topbar" />
        <p className="visually-hidden" role="status">
          Loading the editor
        </p>
      </div>
    );
  if (status !== 'signed-in') return <AuthScreens />;
  return (
    <ChangesProvider>
      <Outlet />
    </ChangesProvider>
  );
}

export const router = createBrowserRouter([
  {
    element: <Gate />,
    children: [
      { path: '/', element: <Navigate to="/pages/home" replace /> },
      { path: '/pages/:pageId', element: <EditorPage /> },
      { path: '/review', element: <ReviewPage /> },
      { path: '/history', element: <HistoryPage /> },
      { path: '/users', element: <UsersPage /> },
      { path: '/shot-list', element: <ShotListPage /> },
      { path: '*', element: <Navigate to="/pages/home" replace /> },
    ],
  },
]);
