import { afterEach, expect, it, vi } from 'vitest';
import { ApiRequestError, clearProfile, currentUser, downloadUrl, fetchProfile, generateCv, login, logout, register, saveProfile } from './api';
import { emptyProfile } from './profile';

afterEach(() => vi.unstubAllGlobals());

it('rejects external download links', () => {
  expect(() => downloadUrl('https://untrusted.example/file.pdf')).toThrow();
});

it('explains network failures', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
  await expect(generateCv({ profile_text: 'p', offer_text: 'o' })).rejects.toThrow('conectar');
});

it('handles non-JSON server errors', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>error</html>', { status: 502 })));
  await expect(generateCv({ profile_text: 'p', offer_text: 'o' })).rejects.toThrow('inesperada');
});

it('handles an invalid response contract', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('null', { status: 201 })));
  await expect(generateCv({ profile_text: 'p', offer_text: 'o' })).rejects.toThrow('inesperada');
});

it.each(['//evil.example/file', '/api/v1/cv/generations/------------------------------------/pdf', '/api/v1/cv/generations/00000000-0000-4000-8000-000000000001/pdf?token=x'])('rejects unsafe download %s', path => {
  expect(() => downloadUrl(path)).toThrow();
});

it('never exposes unexpected server messages', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({error: {code: 'unknown', message: 'PRIVATE internal path'}}), {status: 500})));
  await expect(generateCv({profile_text: 'p', offer_text: 'o'})).rejects.toThrow('Vuelve a intentarlo');
});

it.each([['provider_http_403','403'], ['provider_http_429','cuota'], ['provider_token_limit','incompleta'], ['provider_network','conectar con Gemini']])('explains the safe provider diagnostic %s', async (code, message) => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({error:{code, message:'PRIVATE'}}), {status:502})));
  await expect(generateCv({profile_text:'p',offer_text:'o'})).rejects.toThrow(message);
});

it('rejects a provider response containing an external download link', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({id:'test',status:'completed',download_url:'https://evil.example/cv.pdf'}), {status:201})));
  await expect(generateCv({profile_text:'p',offer_text:'o'})).rejects.toThrow('descarga inválido');
});

it.each([
  ['/api/v1/cv/generations', () => generateCv({ profile_text: 'p', offer_text: 'o' })],
  ['/api/v1/auth/register', () => register('a@b.co', 'a long password')],
  ['/api/v1/auth/login', () => login('a@b.co', 'a long password')],
  ['/api/v1/auth/logout', () => logout()],
  ['/api/v1/auth/me', () => currentUser()],
  ['/api/v1/profile', () => fetchProfile()],
  ['/api/v1/profile', () => saveProfile(emptyProfile)],
  ['/api/v1/profile', () => clearProfile()],
])('sends the session cookie to %s', async (path, call) => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: 'x', status: 'completed', download_url: '/api/v1/cv/generations/00000000-0000-4000-8000-000000000001/pdf', profile: emptyProfile, updated_at: null, missing: [], complete: false }), { status: 200 }));
  vi.stubGlobal('fetch', fetchMock);
  await call().catch(() => {});
  expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining(path), expect.objectContaining({ credentials: 'include' }));
});

it('treats a 401 from /me as no session, not an error', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'failed', error: { code: 'unauthenticated', message: 'x' } }), { status: 401 })));
  await expect(currentUser()).resolves.toBeNull();
});

it('rejects registration with a field-level, non-echoing message', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
    status: 'failed', error: { code: 'invalid_request', message: 'PRIVATE', fields: [{ field: 'email', message: 'Enter a valid email address.' }] },
  }), { status: 422 })));
  const error = await register('not-an-email', 'a long password').catch(e => e);
  expect(error).toBeInstanceOf(ApiRequestError);
  expect((error as ApiRequestError).fields).toEqual({ email: 'Enter a valid email address.' });
  expect((error as ApiRequestError).message).not.toContain('PRIVATE');
});

it('maps profile field errors by path for the form to place', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
    status: 'failed', error: { code: 'invalid_request', message: 'x', fields: [{ field: 'experience.0.start_date', message: 'Invalid.' }] },
  }), { status: 422 })));
  const error = await saveProfile(emptyProfile).catch(e => e);
  expect((error as ApiRequestError).fields).toEqual({ 'experience.0.start_date': 'Invalid.' });
});

it('never throws for logout, even if the request fails', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 500 })));
  await expect(logout()).resolves.toBeUndefined();
});
