import { useEffect, useRef, useState, type FormEvent } from 'react';
import { downloadUrl, generateCv, type GenerationResponse } from '../../lib/api';
import { BrandMark } from '../../components/BrandMark';
import { FileDropzone } from '../../components/FileDropzone';
import { Icon } from '../../components/Icon';
import { useMarkdownFile } from './useMarkdownFile';

export function GenerationForm() {
  const profile = useMarkdownFile();
  const offer = useMarkdownFile();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<GenerationResponse | null>(null);
  const inFlight = useRef(false);
  const form = useRef<HTMLFormElement>(null);
  const download = useRef<HTMLAnchorElement>(null);
  const ready = profile.valid && offer.valid;
  useEffect(() => { if (result) download.current?.focus(); }, [result]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight.current || !ready || !profile.file || !offer.file || result) return;
    inFlight.current = true;
    setLoading(true);
    setError('');
    try {
      setResult(await generateCv({ profile_text: profile.file.content, offer_text: offer.file.content, output_name: 'cv.pdf' }));
    } catch (error) {
      setError(error instanceof Error ? error.message : 'No se pudo generar el CV. Inténtalo de nuevo.');
    } finally {
      inFlight.current = false;
      setLoading(false);
    }
  }
  function reset() {
    profile.remove(); offer.remove(); setResult(null); setError('');
    requestAnimationFrame(() => form.current?.querySelector<HTMLButtonElement>('.drop-target')?.focus());
  }

  return <div className="app-shell">
    <BrandMark />
    <main>
      <section className="intro" aria-labelledby="page-title">
        <p className="eyebrow"><span /> UNA NUEVA OPORTUNIDAD EMPIEZA AQUÍ</p>
        <h1 id="page-title">Tu experiencia.<br />El CV para <em>esa oportunidad.</em></h1>
        <p className="intro-description">Conecta tu perfil con la oferta que te interesa.<br className="desktop-break" /> Obtén un CV adaptado, profesional y listo para descargar.</p>
        <div className="output-details"><span>Un PDF</span><span>Una página</span><span>En inglés</span></div>
      </section>
      <form ref={form} className="workspace" onSubmit={submit} aria-label="Generar un CV adaptado">
        <div className="workspace-heading"><div><p className="eyebrow">EL PUNTO DE PARTIDA</p><h2>Dos archivos. Un CV a medida.</h2></div><span className="format-badge">Markdown <span aria-hidden="true">↗</span> PDF</span></div>
        <div className="upload-grid" aria-busy={loading}>
          <FileDropzone id="profile" number="01" title="Tu perfil profesional" description="Tu experiencia, formación, habilidades y logros. La base de tu próximo CV."
            icon="profile" {...profile} disabled={loading || !!result} onSelect={files => { setError(''); void profile.select(files); }} onRemove={() => { profile.remove(); setError(''); }} />
          <FileDropzone id="offer" number="02" title="Oferta de empleo" description="La descripción del puesto, sus requisitos y lo que busca la empresa."
            icon="briefcase" {...offer} disabled={loading || !!result} onSelect={files => { setError(''); void offer.select(files); }} onRemove={() => { offer.remove(); setError(''); }} />
        </div>
        <div className={`action-area ${result ? 'is-success' : ''}`}>
          <div className="action-copy" role="status" aria-live="polite" aria-atomic="true">
            <span className={`status-symbol ${loading ? 'spinner' : ''}`} aria-hidden="true">{!loading && <Icon name={result || ready ? 'check' : 'upload'} />}</span>
            <div><strong>{result ? 'Tu próximo CV ya está listo.' : loading ? 'Estamos preparando tu CV' : ready ? 'Todo listo para dar el siguiente paso.' : 'Empieza con tus dos archivos'}</strong>
              <p>{result ? 'Descárgalo y revisa los detalles antes de enviarlo.' : loading ? 'La solicitud sigue en curso. Puede tardar varios minutos.' : ready ? 'Tu perfil y la oferta están listos para generar.' : 'Añade tu perfil y la oferta para continuar.'}</p></div>
          </div>
          {result?.download_url ? <div className="result-actions"><a ref={download} className="primary-button" href={downloadUrl(result.download_url)}><Icon name="download" />Descargar PDF</a><button className="text-button" type="button" onClick={reset}>Generar otro CV <span aria-hidden="true">↗</span></button></div>
            : <button className="primary-button" type="submit" disabled={!ready || loading} aria-busy={loading}>{loading ? 'Generando tu CV…' : 'Generar mi CV'}{!loading && <Icon name="arrow" />}</button>}
        </div>
        {error && <div className="generation-error" role="alert"><Icon name="alert" /><div><strong>No hemos podido terminar</strong><p>{error}</p><span>Tus archivos siguen aquí. Puedes volver a intentarlo.</span></div></div>}
        <p className="privacy-note"><Icon name="lock" />Los archivos se leen en tu navegador. Su contenido solo se envía al generar tu CV.</p>
      </form>
      <p className="closing-note">Tu experiencia es el punto de partida. Tú tienes la última palabra.</p>
    </main>
    <footer className="site-footer"><span>autoCV</span><span>Hecho para tu siguiente paso.</span></footer>
  </div>;
}
