import { useEffect, useRef, useState } from 'react';
import { validateMarkdown, type MarkdownFile } from './fileValidation';

export function useMarkdownFile() {
  const [file, setFile] = useState<MarkdownFile | null>(null);
  const [error, setError] = useState('');
  const [reading, setReading] = useState(false);
  const version = useRef(0);
  useEffect(() => () => { version.current++; }, []);
  async function select(files: File[]) {
    const current = ++version.current;
    setError(''); setReading(false);
    if (files.length !== 1) { setError('Selecciona un solo archivo Markdown para este apartado.'); return; }
    setReading(true);
    try {
      const selected = await validateMarkdown(files[0]);
      if (current === version.current) setFile(selected);
    } catch (error) {
      if (current === version.current) setError(error instanceof Error ? error.message : 'No se pudo leer el archivo.');
    } finally { if (current === version.current) setReading(false); }
  }
  function remove() { version.current++; setFile(null); setError(''); setReading(false); }
  return { file, error, reading, select, remove, valid: !!file && !error && !reading };
}
