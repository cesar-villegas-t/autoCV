import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { GenerationForm } from './GenerationForm';
import * as api from '../../lib/api';

vi.mock('../../lib/api', async importOriginal => {
  const actual = await importOriginal<typeof import('../../lib/api')>();
  return { ...actual, fetchProfile: vi.fn(), generateCv: vi.fn() };
});

afterEach(() => { cleanup(); vi.clearAllMocks(); });

const fetchProfile = vi.mocked(api.fetchProfile);
const generateCv = vi.mocked(api.generateCv);
const response = { id: '00000000-0000-4000-8000-000000000001', status: 'completed' as const, error: null,
  download_url: '/api/v1/cv/generations/00000000-0000-4000-8000-000000000001/pdf' };

function offer() {
  fireEvent.change(screen.getByLabelText('Oferta de empleo', { selector: 'input' }),
    { target: { files: [new File(['Job offer'], 'oferta.md')] } });
}

describe('GenerationForm — saved profile', () => {
  it('never contacts the profile endpoint while the upload tab is selected', () => {
    render(<GenerationForm onEditProfile={() => {}} />);
    expect(fetchProfile).not.toHaveBeenCalled();
  });

  it('checks completeness only after switching tabs, and generates with use_saved_profile', async () => {
    fetchProfile.mockResolvedValue({ profile: {} as never, updated_at: null, missing: [], complete: true });
    generateCv.mockResolvedValue(response);
    render(<GenerationForm onEditProfile={() => {}} />);
    fireEvent.click(screen.getByRole('tab', { name: 'Usar mi perfil guardado' }));
    expect(await screen.findByText('Tu perfil guardado está listo para usarse.')).toBeTruthy();
    expect(fetchProfile).toHaveBeenCalledTimes(1);

    offer();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Generar mi CV' }).hasAttribute('disabled')).toBe(false));
    fireEvent.click(screen.getByRole('button', { name: 'Generar mi CV' }));
    await waitFor(() => expect(generateCv).toHaveBeenCalledWith({ use_saved_profile: true, offer_text: 'Job offer', output_name: 'cv.pdf' }));
  });

  it('disables generation and explains what is missing for an incomplete saved profile', async () => {
    fetchProfile.mockResolvedValue({ profile: {} as never, updated_at: null, missing: ['name', 'email'], complete: false });
    render(<GenerationForm onEditProfile={() => {}} />);
    fireEvent.click(screen.getByRole('tab', { name: 'Usar mi perfil guardado' }));
    expect(await screen.findByText(/Falta el nombre, el email/)).toBeTruthy();
    offer();
    expect((screen.getByRole('button', { name: 'Generar mi CV' }) as HTMLButtonElement).disabled).toBe(true);
    expect(generateCv).not.toHaveBeenCalled();
  });

  it('sends the user to the profile editor from the saved-profile card', async () => {
    fetchProfile.mockResolvedValue({ profile: {} as never, updated_at: null, missing: [], complete: true });
    const onEditProfile = vi.fn();
    render(<GenerationForm onEditProfile={onEditProfile} />);
    fireEvent.click(screen.getByRole('tab', { name: 'Usar mi perfil guardado' }));
    fireEvent.click(await screen.findByRole('button', { name: /Editar mi perfil/ }));
    expect(onEditProfile).toHaveBeenCalledTimes(1);
  });

  it('shows an error banner without leaking details when checking the saved profile fails', async () => {
    fetchProfile.mockRejectedValue(new Error('network down'));
    render(<GenerationForm onEditProfile={() => {}} />);
    fireEvent.click(screen.getByRole('tab', { name: 'Usar mi perfil guardado' }));
    expect(await screen.findByText('No se pudo comprobar tu perfil guardado.')).toBeTruthy();
  });
});
