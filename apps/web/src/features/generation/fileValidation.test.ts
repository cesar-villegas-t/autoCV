import { afterEach, expect, it, vi } from 'vitest';
import { validateMarkdown } from './fileValidation';
afterEach(() => vi.restoreAllMocks());

it.each(['', 'text/plain', 'text/markdown', 'text/x-markdown'])('accepts Markdown MIME %s and preserves original content', async type => {
  const content = '\ufeff  # Perfil\r\nCésar — experiencia\n';
  const file = await validateMarkdown(new File([content], 'Perfil.MD', { type }));
  expect(file.content).toBe(content);
});
it('counts Unicode characters like the API, including four-byte characters', async () => {
  const content = '😀'.repeat(100000);
  expect((await validateMarkdown(new File([content], 'unicode.md'))).content).toBe(content);
});
it('rejects malformed UTF-8', async () => {
  await expect(validateMarkdown(new File([new Uint8Array([0xc3, 0x28])], 'bad.md'))).rejects.toThrow('UTF-8');
});
it('rejects binary NUL characters', async () => {
  await expect(validateMarkdown(new File(['abc\0def'], 'bad.md'))).rejects.toThrow('datos no válidos');
});
it('handles reader errors', async () => {
  vi.spyOn(FileReader.prototype, 'readAsArrayBuffer').mockImplementation(function (this: FileReader) {
    this.dispatchEvent(new ProgressEvent('error'));
  });
  await expect(validateMarkdown(new File(['data'], 'read.md'))).rejects.toThrow('No se pudo leer');
});
