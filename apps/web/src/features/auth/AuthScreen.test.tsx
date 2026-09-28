import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { AuthProvider, useAuth } from './AuthContext';
import { AuthScreen } from './AuthScreen';

function Harness() {
  const { user } = useAuth();
  return user ? <p>Hola, {user.email}</p> : <AuthScreen />;
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

function meResponse(status = 401) {
  return new Response(JSON.stringify({ status: 'failed', error: { code: 'unauthenticated', message: 'x' } }), { status });
}

function renderScreen() {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(meResponse());
  vi.stubGlobal('fetch', fetchMock);
  render(<AuthProvider><Harness /></AuthProvider>);
  return fetchMock;
}

describe('AuthScreen', () => {
  it('registers, sends credentials with the session cookie and shows field errors without echoing input', async () => {
    const fetchMock = renderScreen();
    await screen.findByRole('heading', { name: 'Inicia sesión' });
    fireEvent.click(screen.getByRole('button', { name: 'Crea una' }));
    await screen.findByRole('heading', { name: 'Crea tu cuenta' });

    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
      status: 'failed', error: { code: 'weak_password', message: 'La contraseña debe tener entre 10 y 128 caracteres.' },
    }), { status: 422 }));
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'ana@example.com' } });
    fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'short' } });
    fireEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }));

    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('entre 10 y 128');
    const call = fetchMock.mock.calls.at(-1)!;
    expect(call[0]).toContain('/api/v1/auth/register');
    expect((call[1] as RequestInit).credentials).toBe('include');
    expect(JSON.parse((call[1] as RequestInit).body as string)).toEqual({ email: 'ana@example.com', password: 'short' });
  });

  it('logs in successfully and hands the user to the app', async () => {
    const fetchMock = renderScreen();
    await screen.findByRole('heading', { name: 'Inicia sesión' });
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ id: '1', email: 'ana@example.com', created_at: '2030-01-01T00:00:00Z' }), { status: 200 }));
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'ana@example.com' } });
    fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'correct horse battery' } });
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }));
    expect(await screen.findByText('Hola, ana@example.com')).toBeTruthy();
  });

  it('shows a uniform error for invalid credentials', async () => {
    const fetchMock = renderScreen();
    await screen.findByRole('heading', { name: 'Inicia sesión' });
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ status: 'failed', error: { code: 'invalid_credentials', message: 'Invalid email or password.' } }), { status: 401 }));
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'ana@example.com' } });
    fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'wrong password here' } });
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }));
    expect((await screen.findByRole('alert')).textContent).toContain('incorrectos');
  });
});
