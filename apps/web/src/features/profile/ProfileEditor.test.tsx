import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { ProfileEditor } from './ProfileEditor';
import { emptyProfile } from '../../lib/profile';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

function profileResponse(overrides: Partial<typeof emptyProfile> = {}, extra: Record<string, unknown> = {}) {
  return new Response(JSON.stringify({
    profile: { ...emptyProfile, ...overrides }, updated_at: null,
    missing: ['name', 'email', 'experience_or_education'], complete: false, ...extra,
  }), { status: 200 });
}

function stub(...responses: Response[]) {
  const fetchMock = vi.fn<typeof fetch>();
  for (const response of responses) fetchMock.mockResolvedValueOnce(response);
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

async function renderEditor(...responses: Response[]) {
  const fetchMock = stub(...responses);
  render(<ProfileEditor />);
  await screen.findByRole('heading', { name: 'Tu perfil' });
  return fetchMock;
}

describe('ProfileEditor', () => {
  it('loads the saved profile and shows what is missing', async () => {
    await renderEditor(profileResponse({ first_name: 'Ana' }));
    expect((screen.getByLabelText('Nombre') as HTMLInputElement).value).toBe('Ana');
    expect(screen.getByText(/Falta:/).textContent).toContain('el email');
  });

  it('shows a complete badge once nothing is missing', async () => {
    await renderEditor(profileResponse({ first_name: 'Ana', email: 'ana@example.com',
      experience: [{ company: 'Bdeo', title: 'Lead', start_date: '2024-01', end_date: null, current: true, description: '' }] },
      { missing: [], complete: true }));
    expect(screen.getByText('Perfil completo')).toBeTruthy();
  });

  it('adds, fills and saves a new work experience block', async () => {
    const fetchMock = await renderEditor(
      profileResponse(),
      profileResponse({
        first_name: 'Ana', email: 'ana@example.com',
        experience: [{ company: 'Bdeo', title: 'Growth Lead', start_date: '2024-10', end_date: null, current: true, description: 'Cut churn' }],
      }, { missing: [], complete: true }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Añadir experiencia' }));
    const card = screen.getByText('Experiencia 1').closest('.block-card') as HTMLElement;
    fireEvent.change(within(card).getByLabelText('Empresa'), { target: { value: 'Bdeo' } });
    fireEvent.change(within(card).getByLabelText('Puesto'), { target: { value: 'Growth Lead' } });
    fireEvent.change(within(card).getByLabelText('Inicio'), { target: { value: '2024-10' } });
    fireEvent.click(within(card).getByLabelText('Actualmente en este puesto'));
    fireEvent.change(within(card).getByLabelText('Descripción / más info'), { target: { value: 'Cut churn' } });
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Ana' } });
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'ana@example.com' } });

    fireEvent.click(screen.getByRole('button', { name: 'Guardar perfil' }));
    await waitFor(() => expect(screen.getByText('Perfil completo')).toBeTruthy());

    const call = fetchMock.mock.calls.at(-1)!;
    expect(call[0]).toContain('/api/v1/profile');
    expect((call[1] as RequestInit).method).toBe('PUT');
    const body = JSON.parse((call[1] as RequestInit).body as string);
    expect(body.experience).toEqual([{ company: 'Bdeo', title: 'Growth Lead', start_date: '2024-10', end_date: null, current: true, description: 'Cut churn' }]);
  });

  it('disables the end date while "current" is checked and clears it', async () => {
    await renderEditor(profileResponse({
      experience: [{ company: 'A', title: 'B', start_date: '2020-01', end_date: '2021-01', current: false, description: '' }],
    }));
    const card = screen.getByText('B · A').closest('.block-card') as HTMLElement;
    fireEvent.click(within(card).getByLabelText('Actualmente en este puesto'));
    const end = within(card).getByLabelText('Fin') as HTMLInputElement;
    expect(end.disabled).toBe(true);
    expect(end.value).toBe('');
  });

  it('reorders and removes experience blocks', async () => {
    await renderEditor(profileResponse({
      experience: [
        { company: 'First', title: 'A', start_date: '2020-01', end_date: '2021-01', current: false, description: '' },
        { company: 'Second', title: 'B', start_date: '2021-02', end_date: null, current: true, description: '' },
      ],
    }));
    fireEvent.click(screen.getByRole('button', { name: 'Bajar A · First' }));
    const cards = screen.getAllByLabelText('Empresa');
    expect(cards.map(input => (input as HTMLInputElement).value)).toEqual(['Second', 'First']);
    fireEvent.click(screen.getByRole('button', { name: 'Eliminar B · Second' }));
    expect(screen.getAllByLabelText('Empresa')).toHaveLength(1);
  });

  it('places field-level errors from the API next to the offending input, without touching unrelated blocks', async () => {
    const fetchMock = await renderEditor(profileResponse({
      experience: [{ company: 'A', title: 'B', start_date: '2020-01', end_date: null, current: true, description: '' }],
    }));
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
      status: 'failed', error: { code: 'invalid_request', message: 'x',
        fields: [{ field: 'experience.0.company', message: 'PRIVATE reason' }] },
    }), { status: 422 }));
    fireEvent.click(screen.getByRole('button', { name: 'Guardar perfil' }));
    const alert = await screen.findByText('PRIVATE reason');
    expect(alert.closest('.block-card')?.textContent).toContain('B · A');
  });

  it('clears the profile after a two-step confirmation', async () => {
    const fetchMock = await renderEditor(profileResponse({ first_name: 'Ana' }));
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    fireEvent.click(screen.getByRole('button', { name: 'Borrar perfil' }));
    fireEvent.click(screen.getByRole('button', { name: 'Sí, borrar' }));
    await waitFor(() => expect((screen.getByLabelText('Nombre') as HTMLInputElement).value).toBe(''));
    expect(fetchMock.mock.calls.at(-1)![1]).toMatchObject({ method: 'DELETE' });
  });

  it('adds and removes relocation tags', async () => {
    await renderEditor(profileResponse());
    const input = screen.getByLabelText('Posibles relocations');
    fireEvent.change(input, { target: { value: 'Barcelona' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(screen.getByText('Barcelona')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Quitar Barcelona' }));
    expect(screen.queryByText('Barcelona')).toBeNull();
  });

  it('shows a load error without crashing when the profile cannot be fetched', async () => {
    stub(new Response(JSON.stringify({ status: 'failed', error: { code: 'unauthenticated', message: 'x' } }), { status: 401 }));
    render(<ProfileEditor />);
    expect(await screen.findByRole('alert')).toBeTruthy();
  });
});
