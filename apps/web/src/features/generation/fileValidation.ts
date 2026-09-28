export const MAX_FILE_BYTES = 400_000;
export const MAX_CHARACTERS = 100_000;
export interface MarkdownFile { name: string; size: number; content: string }
const allowedMime = new Set(['', 'text/markdown', 'text/x-markdown', 'text/plain']);

export function readBuffer(file: File): Promise<ArrayBuffer> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => reader.result instanceof ArrayBuffer ? resolve(reader.result) : reject(new Error('No se pudo leer el archivo. Vuelve a seleccionarlo.'));
    reader.onerror = reader.onabort = () => reject(new Error('No se pudo leer el archivo. Vuelve a seleccionarlo.'));
    try { reader.readAsArrayBuffer(file); }
    catch { reject(new Error('No se pudo leer el archivo. Vuelve a seleccionarlo.')); }
  });
}
export async function validateMarkdown(file: File): Promise<MarkdownFile> {
  if (!/^.+\.md$/i.test(file.name) || /[\x00-\x1f/\\]/.test(file.name)) throw new Error('Selecciona un archivo Markdown con extensión .md.');
  if (!allowedMime.has(file.type.toLowerCase().split(';')[0].trim())) throw new Error('El tipo de este archivo no corresponde a un documento Markdown.');
  if (!file.size) throw new Error('El archivo está vacío. Añade contenido y vuelve a seleccionarlo.');
  if (file.size > MAX_FILE_BYTES) throw new Error('El archivo supera los 400 kB permitidos. Selecciona uno más pequeño.');
  const buffer = await readBuffer(file);
  let content: string;
  try {
    // Preserve whitespace and BOM; reject malformed UTF-8.
    content = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(buffer);
  } catch { throw new Error('No se pudo leer como UTF-8. Guarda el Markdown con esa codificación.'); }
  if (!content.trim()) throw new Error('El archivo está vacío. Añade contenido y vuelve a seleccionarlo.');
  if (content.includes('\0')) throw new Error('El archivo contiene datos no válidos. Selecciona un Markdown de texto.');
  // Match Python/Pydantic code points instead of JavaScript UTF-16 units.
  if (Array.from(content).length > MAX_CHARACTERS) throw new Error('El contenido supera los 100.000 caracteres permitidos. Reduce el texto.');
  return { name: file.name, size: file.size, content };
}
export function formatSize(bytes: number): string {
  return bytes < 1000 ? `${bytes} B` : `${new Intl.NumberFormat('es', { maximumFractionDigits: 1 }).format(bytes / 1000)} kB`;
}
