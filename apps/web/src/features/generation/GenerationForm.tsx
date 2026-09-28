import { useEffect, useRef, useState, type FormEvent } from 'react';
import { downloadUrl, fetchProfile, generateCv, type GenerationResponse } from '../../lib/api';
import { FileDropzone } from '../../components/FileDropzone';
import { Icon } from '../../components/Icon';
import { describeMissing } from '../../lib/profile';
import { useMarkdownFile } from './useMarkdownFile';

type ProfileSource = 'upload' | 'saved';
type SavedProfileStatus = 'idle' | 'loading' | 'error' | { complete: boolean; missing: string[] };

export function GenerationForm({ onEditProfile }: { onEditProfile: () => void }) {
  const [source, setSource] = useState<ProfileSource>('upload');
  const [savedStatus, setSavedStatus] = useState<SavedProfileStatus>('idle');
  const profile = useMarkdownFile();
  const offer = useMarkdownFile();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<GenerationResponse | null>(null);
  const inFlight = useRef(false);
  const savedProfileRequested = useRef(false);
  const form = useRef<HTMLFormElement>(null);
  const download = useRef<HTMLAnchorElement>(null);
  const savedReady = typeof savedStatus === 'object' && savedStatus.complete;
  const ready = (source === 'upload' ? profile.valid : savedReady) && offer.valid;
  useEffect(() => { if (result) download.current?.focus(); }, [result]);

  // Loaded lazily: choosing the file-upload tab never touches the network. Guarded by a ref,
  // not by savedStatus itself, so the effect does not re-run (and cancel itself) on its own update.
  useEffect(() => {
    if (source !== 'saved' || savedProfileRequested.current) return;
    savedProfileRequested.current = true;
    let active = true;
    setSavedStatus('loading');
    fetchProfile()
      .then(response => { if (active) setSavedStatus({ complete: response.complete, missing: response.missing }); })
      .catch(() => { if (active) setSavedStatus('error'); });
    return () => { active = false; };
  }, [source]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight.current || !ready || !offer.file || result) return;
    if (source === 'upload' && !profile.file) return;
    inFlight.current = true;
    setLoading(true);
    setError('');
    try {
      setResult(await generateCv(source === 'saved'
        ? { use_saved_profile: true, offer_text: offer.file.content, output_name: 'cv.pdf' }
        : { profile_text: profile.file!.content, offer_text: offer.file.content, output_name: 'cv.pdf' }));
    } catch (error) {
      setError(error instanceof Error ? error.message : 'No se pudo generar el CV. Inténtalo de nuevo.');
    } finally {
      inFlight.current = false;
      setLoading(false);
    }
  }
  function reset() {
    profile.remove(); offer.remove(); setResult(null); setError('');
    savedProfileRequested.current = false; setSavedStatus('idle');
    requestAnimationFrame(() => form.current?.querySelector<HTMLButtonElement>('.drop-target')?.focus());
  }

  return <div>
    <section className="intro" aria-labelledby="page-title">
      <p className="eyebrow"><span /> UNA NUEVA OPORTUNIDAD EMPIEZA AQUÍ</p>
      <h1 id="page-title">Tu experiencia.<br />El CV para <em>esa oportunidad.</em></h1>
      <p className="intro-description">Conecta tu perfil con la oferta que te interesa.<br className="desktop-break" /> Obtén un CV adaptado, profesional y listo para descargar.</p>
      <div className="output-details"><span>Un PDF</span><span>Una página</span><span>En inglés</span></div>
    </section>
    <form ref={form} className="workspace" onSubmit={submit} aria-label="Generar un CV adaptado">
      <div className="workspace-heading"><div><p className="eyebrow">EL PUNTO DE PARTIDA</p><h2>Tu perfil y la oferta. Un CV a medida.</h2></div><span className="format-badge">Markdown <span aria-hidden="true">↗</span> PDF</span></div>
      <div className="source-tabs" role="tablist" aria-label="Origen del perfil">
        <button type="button" role="tab" className="source-tab" aria-selected={source === 'upload'} disabled={loading || !!result}
          onClick={() => setSource('upload')}>Subir archivo</button>
        <button type="button" role="tab" className="source-tab" aria-selected={source === 'saved'} disabled={loading || !!result}
          onClick={() => setSource('saved')}>Usar mi perfil guardado</button>
      </div>
      <div className="upload-grid" aria-busy={loading}>
        {source === 'upload'
          ? <FileDropzone id="profile" number="01" title="Tu perfil profesional" description="Tu experiencia, formación, habilidades y logros. La base de tu próximo CV."
              icon="profile" {...profile} disabled={loading || !!result} onSelect={files => { setError(''); void profile.select(files); }} onRemove={() => { profile.remove(); setError(''); }} />
          : <SavedProfileStatusCard status={savedStatus} onEditProfile={onEditProfile} />}
        <FileDropzone id="offer" number="02" title="Oferta de empleo" description="La descripción del puesto, sus requisitos y lo que busca la empresa."
          icon="briefcase" {...offer} disabled={loading || !!result} onSelect={files => { setError(''); void offer.select(files); }} onRemove={() => { offer.remove(); setError(''); }} />
      </div>
      <div className={`action-area ${result ? 'is-success' : ''}`}>
        <div className="action-copy" role="status" aria-live="polite" aria-atomic="true">
          <span className={`status-symbol ${loading ? 'spinner' : ''}`} aria-hidden="true">{!loading && <Icon name={result || ready ? 'check' : 'upload'} />}</span>
          <div><strong>{result ? 'Tu próximo CV ya está listo.' : loading ? 'Estamos preparando tu CV' : ready ? 'Todo listo para dar el siguiente paso.' : 'Completa tu perfil y la oferta'}</strong>
            <p>{result ? 'Descárgalo y revisa los detalles antes de enviarlo.' : loading ? 'La solicitud sigue en curso. Puede tardar varios minutos.' : ready ? 'Tu perfil y la oferta están listos para generar.' : 'Añade tu perfil y la oferta para continuar.'}</p></div>
        </div>
        {result?.download_url ? <div className="result-actions"><a ref={download} className="primary-button" href={downloadUrl(result.download_url)}><Icon name="download" />Descargar PDF</a><button className="text-button" type="button" onClick={reset}>Generar otro CV <span aria-hidden="true">↗</span></button></div>
          : <button className="primary-button" type="submit" disabled={!ready || loading} aria-busy={loading}>{loading ? 'Generando tu CV…' : 'Generar mi CV'}{!loading && <Icon name="arrow" />}</button>}
      </div>
      {error && <div className="generation-error" role="alert"><Icon name="alert" /><div><strong>No hemos podido terminar</strong><p>{error}</p><span>Tus archivos siguen aquí. Puedes volver a intentarlo.</span></div></div>}
      <p className="privacy-note"><Icon name="lock" />{source === 'upload' ? 'Los archivos se leen en tu navegador. Su contenido solo se envía al generar tu CV.' : 'Tu perfil guardado solo se usa para generar este CV.'}</p>
    </form>
    <p className="closing-note">Tu experiencia es el punto de partida. Tú tienes la última palabra.</p>
  </div>;
}

function SavedProfileStatusCard({ status, onEditProfile }: { status: SavedProfileStatus; onEditProfile: () => void }) {
  return <section className="file-field saved-profile-card" aria-labelledby="saved-profile-title">
    <div className="field-heading"><span className="step-number">01</span><h2 id="saved-profile-title">Tu perfil profesional</h2></div>
    <div className="saved-profile-body">
      {status === 'loading' && <p role="status">Comprobando tu perfil guardado…</p>}
      {status === 'error' && <p className="field-error" role="alert"><Icon name="alert" />No se pudo comprobar tu perfil guardado.</p>}
      {typeof status === 'object' && status.complete && <p className="saved-profile-ready"><Icon name="check" />Tu perfil guardado está listo para usarse.</p>}
      {typeof status === 'object' && !status.complete && (
        <p className="field-error" role="alert"><Icon name="alert" />Falta {describeMissing(status.missing)} en tu perfil guardado.</p>
      )}
      <button type="button" className="text-button" onClick={onEditProfile}>Editar mi perfil <span aria-hidden="true">↗</span></button>
    </div>
  </section>;
}
