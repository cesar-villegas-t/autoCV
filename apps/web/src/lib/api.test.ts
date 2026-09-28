import { afterEach, expect, it, vi } from 'vitest';
import { downloadUrl, generateCv } from './api';

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
