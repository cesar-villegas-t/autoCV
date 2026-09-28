import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { GenerationForm } from './GenerationForm';

const response = { id: '00000000-0000-4000-8000-000000000001', status: 'completed', error: null,
  download_url: '/api/v1/cv/generations/00000000-0000-4000-8000-000000000001/pdf' };
const profile = () => screen.getByLabelText<HTMLInputElement>('Tu perfil profesional', { selector: 'input' });
const offer = () => screen.getByLabelText<HTMLInputElement>('Oferta de empleo', { selector: 'input' });
const button = () => screen.getByRole<HTMLButtonElement>('button', { name: 'Generar mi CV' });
function choose(input: HTMLInputElement, name: string, text = 'contenido', type = '') {
  fireEvent.change(input, { target: { files: [new File([text], name, { type })] } });
}
async function fill() {
  choose(profile(), 'perfil.md', '  Candidate facts\r\n');
  choose(offer(), 'oferta.md', 'Job offer');
  await waitFor(() => expect(button().disabled).toBe(false));
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('generation flow', () => {
  it('sends exact text, shows progress, prevents duplicate requests, downloads and resets', async () => {
    let finish!: (value: Response) => void;
    const fetchMock = vi.fn<typeof fetch>(() => new Promise<Response>(resolve => { finish = resolve; }));
    vi.stubGlobal('fetch', fetchMock);
    render(<GenerationForm onEditProfile={() => {}} />);
    expect(button().disabled).toBe(true);
    await fill();
    expect(fetchMock).not.toHaveBeenCalled();
    fireEvent.click(button());
    fireEvent.submit(screen.getByRole('form'));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.getByRole<HTMLButtonElement>('button', { name: 'Generando tu CV…' }).disabled).toBe(true);
    expect(screen.getByText('Estamos preparando tu CV').closest('[role=status]')?.getAttribute('aria-live')).toBe('polite');
    expect(profile().disabled).toBe(true);
    expect(JSON.parse(fetchMock.mock.calls[0]![1]!.body as string)).toEqual({
      profile_text: '  Candidate facts\r\n', offer_text: 'Job offer', output_name: 'cv.pdf',
    });
    finish(new Response(JSON.stringify(response), { status: 201 }));
    const link = await screen.findByRole<HTMLAnchorElement>('link', { name: 'Descargar PDF' });
    expect(link.href).toBe('http://127.0.0.1:8000' + response.download_url);
    expect(link.target).toBe('');
    expect(document.activeElement).toBe(link);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: /Generar otro CV/ }));
    expect(button().disabled).toBe(true);
    expect(screen.queryByText('perfil.md')).toBeNull();
    await waitFor(() => expect(document.activeElement?.getAttribute('aria-label')).toBe('Seleccionar tu perfil profesional'));
  });

  it('preserves files on backend failure and retries successfully', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ status: 'failed',
      error: { code: 'provider_error', message: 'PRIVATE provider details' } }), { status: 502 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(response), { status: 201 }));
    vi.stubGlobal('fetch', fetchMock);
    render(<GenerationForm onEditProfile={() => {}} />);
    await fill();
    fireEvent.click(button());
    expect((await screen.findByRole('alert')).textContent).toContain('Vuelve a intentarlo');
    expect(screen.getByRole('alert').textContent).not.toContain('PRIVATE');
    expect(screen.getByText('perfil.md')).toBeTruthy();
    expect(button().disabled).toBe(false);
    fireEvent.click(button());
    expect(await screen.findByRole('link', { name: 'Descargar PDF' })).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('supports drag and drop, replacement, removal and reselecting the same file', async () => {
    render(<GenerationForm onEditProfile={() => {}} />);
    const zone = profile().closest('.dropzone')!;
    fireEvent.dragEnter(zone, { dataTransfer: { files: [] } });
    expect(zone.classList.contains('is-dragging')).toBe(true);
    fireEvent.drop(zone, { dataTransfer: { files: [new File(['Profile'], 'first.md')] } });
    await screen.findByText('first.md');
    expect(zone.classList.contains('is-dragging')).toBe(false);
    expect(button().disabled).toBe(true);
    choose(profile(), 'second.md');
    await screen.findByText('second.md');
    expect(screen.queryByText('first.md')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Retirar tu perfil profesional' }));
    expect(screen.queryByText('second.md')).toBeNull();
    choose(profile(), 'second.md');
    await screen.findByText('second.md');
    expect(profile().value).toBe('');
  });

  it.each([
    ['bad.pdf', 'data', '', '.md'], ['empty.md', '', '', 'vacío'],
    ['space.md', ' \r\n ', '', 'vacío'], ['binary.md', 'data', 'image/png', 'tipo'],
    ['large.md', 'x'.repeat(400001), '', '400 kB'],
    ['long.md', 'x'.repeat(100001), '', '100.000'],
  ])('reports accessible validation for %s', async (name, text, mime, message) => {
    render(<GenerationForm onEditProfile={() => {}} />);
    choose(profile(), name, text, mime);
    const error = await screen.findByRole('alert');
    expect(error.textContent).toContain(message);
    expect(profile().getAttribute('aria-describedby')).toContain(error.id);
    expect(profile().getAttribute('aria-invalid')).toBe('true');
    expect(button().disabled).toBe(true);
  });

  it('rejects multiple dropped files and keeps previously selected files', async () => {
    render(<GenerationForm onEditProfile={() => {}} />);
    await fill();
    fireEvent.drop(profile().closest('.dropzone')!, { dataTransfer: { files: [new File(['a'], 'a.md'), new File(['b'], 'b.md')] } });
    expect((await screen.findByRole('alert')).textContent).toContain('un solo archivo');
    expect(screen.getByText('perfil.md')).toBeTruthy();
    expect(button().disabled).toBe(true);
  });

  it('has labelled keyboard controls that open the file picker', () => {
    render(<GenerationForm onEditProfile={() => {}} />);
    const open = vi.spyOn(profile(), 'click');
    fireEvent.click(screen.getByRole('button', { name: 'Seleccionar tu perfil profesional' }));
    expect(open).toHaveBeenCalledOnce();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
  });
});
