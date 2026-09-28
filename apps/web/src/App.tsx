import { useState } from 'react';
import { BrandMark } from './components/BrandMark';
import { Icon } from './components/Icon';
import { AuthScreen } from './features/auth/AuthScreen';
import { useAuth } from './features/auth/AuthContext';
import { GenerationForm } from './features/generation/GenerationForm';
import { ProfileEditor } from './features/profile/ProfileEditor';

type View = 'generate' | 'profile';

export function App() {
  const { user, ready, logout } = useAuth();
  const [view, setView] = useState<View>('generate');

  if (!ready) {
    return <div className="app-shell"><BrandMark /><main><p role="status" className="loading-note">Cargando…</p></main></div>;
  }

  return <div className="app-shell">
    <BrandMark />
    {user && <nav className="app-nav" aria-label="Secciones">
      <div className="app-nav-tabs">
        <button type="button" className="nav-tab" aria-current={view === 'generate' || undefined} onClick={() => setView('generate')}>Generar CV</button>
        <button type="button" className="nav-tab" aria-current={view === 'profile' || undefined} onClick={() => setView('profile')}>
          <Icon name="user" />Mi perfil
        </button>
      </div>
      <div className="app-nav-account">
        <span className="app-nav-email">{user.email}</span>
        <button type="button" className="text-button" onClick={() => void logout()}><Icon name="logout" />Cerrar sesión</button>
      </div>
    </nav>}
    <main>
      {!user
        ? <AuthScreen />
        : view === 'profile'
          ? <ProfileEditor />
          : <GenerationForm onEditProfile={() => setView('profile')} />}
    </main>
    <footer className="site-footer"><span>autoCV</span><span>Hecho para tu siguiente paso.</span></footer>
  </div>;
}
