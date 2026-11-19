import { Navigate, Outlet, createBrowserRouter } from 'react-router-dom';
import { useAuth } from './auth/AuthContext.jsx';
import AuthScreens from './auth/AuthScreens.jsx';
import { ChangesProvider } from './shell/ChangesContext.jsx';

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

// Route-level code splitting: each screen (the editor with Tiptap and dnd-kit above all) is its
// own chunk, so the sign-in screen loads only the shell. The chunk is fetched on first visit.
const page = (load) => () => load().then((m) => ({ Component: m.default }));

export const router = createBrowserRouter([
  {
    element: <Gate />,
    children: [
      { path: '/', element: <Navigate to="/pages/home" replace /> },
      { path: '/pages/:pageId', lazy: page(() => import('./editor/EditorPage.jsx')) },
      { path: '/review', lazy: page(() => import('./review/ReviewPage.jsx')) },
      { path: '/history', lazy: page(() => import('./history/HistoryPage.jsx')) },
      { path: '/users', lazy: page(() => import('./users/UsersPage.jsx')) },
      { path: '/messages', lazy: page(() => import('./messages/MessagesPage.jsx')) },
      { path: '/shot-list', lazy: page(() => import('./help/ShotListPage.jsx')) },
      { path: '*', element: <Navigate to="/pages/home" replace /> },
    ],
  },
]);
