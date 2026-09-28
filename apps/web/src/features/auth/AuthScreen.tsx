import { useState, type FormEvent } from 'react';
import { Icon } from '../../components/Icon';
import { useAuth } from './AuthContext';

export function AuthScreen() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const { login, register } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const isRegister = mode === 'register';

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;
    setLoading(true);
    setError('');
    try {
      await (isRegister ? register(email, password) : login(email, password));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudo completar la solicitud.');
    } finally {
      setLoading(false);
    }
  }

  function switchMode(next: 'login' | 'register') {
    setMode(next);
    setError('');
    setPassword('');
  }

  return <section className="auth-shell" aria-labelledby="auth-title">
    <div className="auth-card">
      <h1 id="auth-title">{isRegister ? 'Crea tu cuenta' : 'Inicia sesión'}</h1>
      <p className="auth-subtitle">
        {isRegister ? 'Guarda tu perfil y genera CVs adaptados en segundos.' : 'Accede para usar tu perfil guardado.'}
      </p>
      <form onSubmit={submit} aria-label={isRegister ? 'Crear cuenta' : 'Iniciar sesión'}>
        <div className="form-field">
          <label htmlFor="auth-email">Email</label>
          <input id="auth-email" type="email" autoComplete="email" required value={email}
            onChange={event => setEmail(event.target.value)} disabled={loading} />
        </div>
        <div className="form-field">
          <label htmlFor="auth-password">Contraseña</label>
          <input id="auth-password" type="password" minLength={isRegister ? 10 : undefined} maxLength={128}
            autoComplete={isRegister ? 'new-password' : 'current-password'} required value={password}
            onChange={event => setPassword(event.target.value)} disabled={loading}
            aria-describedby={isRegister ? 'auth-password-hint' : undefined} />
          {isRegister && <p className="field-hint" id="auth-password-hint">Entre 10 y 128 caracteres.</p>}
        </div>
        {error && <p className="field-error" role="alert"><Icon name="alert" />{error}</p>}
        <button className="primary-button auth-submit" type="submit" disabled={loading} aria-busy={loading}>
          {loading ? 'Un momento…' : isRegister ? 'Crear cuenta' : 'Iniciar sesión'}
        </button>
      </form>
      <p className="auth-switch">
        {isRegister ? '¿Ya tienes cuenta?' : '¿Aún no tienes cuenta?'}{' '}
        <button type="button" className="text-button" onClick={() => switchMode(isRegister ? 'login' : 'register')}>
          {isRegister ? 'Inicia sesión' : 'Crea una'}
        </button>
      </p>
    </div>
  </section>;
}

