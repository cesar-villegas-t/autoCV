import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { App } from './App';
import { AuthProvider } from './features/auth/AuthContext';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

function stubFetch(...responses: Response[]) {
  const fetchMock = vi.fn<typeof fetch>();
  for (const response of responses) fetchMock.mockResolvedValueOnce(response);
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

const unauthenticated = () => new Response(JSON.stringify({ status: 'failed', error: { code: 'unauthenticated', message: 'x' } }), { status: 401 });
const user = () => new Response(JSON.stringify({ id: '1', email: 'ana@example.com', created_at: '2030-01-01T00:00:00Z' }), { status: 200 });
const emptyProfileResponse = () => new Response(JSON.stringify({
  profile: { first_name: '', last_name: '', location: '', relocations: [], phone: '', email: '', linkedin: '', links: [],
    summary: '', experience: [], education: [], achievements: [], projects: [], skills: '', languages: [] },
  updated_at: null, missing: ['name', 'email', 'experience_or_education'], complete: false,
}), { status: 200 });

describe('App', () => {
  it('shows the login screen while signed out', async () => {
    stubFetch(unauthenticated());
    render(<AuthProvider><App /></AuthProvider>);
    expect(await screen.findByRole('heading', { name: 'Inicia sesión' })).toBeTruthy();
    expect(screen.queryByLabelText('Secciones')).toBeNull();
  });

  it('shows the generation form and lets a signed-in user switch to their profile and back', async () => {
    stubFetch(user());
    render(<AuthProvider><App /></AuthProvider>);
    expect(await screen.findByRole('button', { name: 'Generar mi CV' })).toBeTruthy();
    expect(screen.getByText('ana@example.com')).toBeTruthy();

    stubFetch(emptyProfileResponse());
    fireEvent.click(screen.getByRole('button', { name: 'Mi perfil' }));
    expect(await screen.findByRole('heading', { name: 'Tu perfil' })).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: 'Generar CV' }));
    expect(await screen.findByRole('button', { name: 'Generar mi CV' })).toBeTruthy();
  });

  it('returns to the login screen after logging out', async () => {
    stubFetch(user());
    render(<AuthProvider><App /></AuthProvider>);
    await screen.findByText('ana@example.com');
    stubFetch(new Response(null, { status: 204 }));
    fireEvent.click(screen.getByRole('button', { name: /Cerrar sesión/ }));
    expect(await screen.findByRole('heading', { name: 'Inicia sesión' })).toBeTruthy();
  });
});
