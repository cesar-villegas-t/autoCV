import { useRef, useState, type DragEvent } from 'react';
import { Icon } from './Icon';
import { formatSize, type MarkdownFile } from '../features/generation/fileValidation';
interface Props {
  id: string; number: string; title: string; description: string; icon: 'profile' | 'briefcase';
  file: MarkdownFile | null; error: string; reading: boolean; disabled: boolean;
  onSelect: (files: File[]) => void; onRemove: () => void;
}
export function FileDropzone({ id, number, title, description, icon, file, error, reading, disabled, onSelect, onRemove }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const target = useRef<HTMLButtonElement>(null);
  const depth = useRef(0);
  const [dragging, setDragging] = useState(false);
  const hintId = `${id}-hint`, errorId = `${id}-error`;
  function enter(event: DragEvent) { event.preventDefault(); if (!disabled) { depth.current++; setDragging(true); } }
  function leave(event: DragEvent) { event.preventDefault(); if (--depth.current <= 0) { depth.current = 0; setDragging(false); } }
  function drop(event: DragEvent) { event.preventDefault(); depth.current = 0; setDragging(false); if (!disabled) onSelect(Array.from(event.dataTransfer.files)); }
  return <section className="file-field" aria-labelledby={`${id}-title`}>
    <div className="field-heading"><span className="step-number">{number}</span><h2 id={`${id}-title`}>{title}</h2></div>
    <p className="field-description" id={hintId}>{description}</p>
    <div className={`dropzone ${file ? 'has-file' : ''} ${error ? 'has-error' : ''} ${dragging && !disabled ? 'is-dragging' : ''}`}
      onDragEnter={enter} onDragLeave={leave} onDragOver={event => { event.preventDefault(); event.dataTransfer.dropEffect = disabled ? 'none' : 'copy'; }} onDrop={drop}>
      <input ref={input} id={id} className="visually-hidden" tabIndex={-1} type="file" accept=".md" aria-label={title}
        aria-describedby={`${hintId} ${error ? errorId : ''}`} aria-invalid={!!error} disabled={disabled}
        onChange={event => { const files = Array.from(event.target.files || []); event.target.value = ''; if (files.length) onSelect(files); }} />
      <button ref={target} className="drop-target" type="button" disabled={disabled} onClick={() => input.current?.click()}
        aria-label={`${file ? 'Sustituir' : 'Seleccionar'} ${title.toLowerCase()}`} aria-describedby={`${hintId} ${error ? errorId : ''}`} aria-invalid={!!error}>
        <span className="file-icon"><Icon name={file ? 'profile' : icon} />{file && <span className="file-check"><Icon name="check" /></span>}</span>
        {file ? <><strong className="file-name" title={file.name}>{file.name}</strong><span className="file-meta">{formatSize(file.size)} <span aria-hidden="true">·</span> Markdown</span><span className="select-label">Sustituir archivo</span></>
          : <><strong>{dragging ? 'Suelta aquí tu Markdown' : 'Arrastra tu archivo .md aquí'}</strong><span className="or-label">o selecciona desde tu equipo</span><span className="select-label"><Icon name="upload" />Seleccionar archivo</span></>}
      </button>
      {file && <button className="remove-file" type="button" aria-label={`Retirar ${title.toLowerCase()}`} disabled={disabled} onClick={() => { onRemove(); target.current?.focus(); }}><Icon name="close" /></button>}
      <span className="file-status" role="status">{reading ? 'Leyendo archivo…' : file && !error ? 'Archivo listo' : ''}</span>
    </div>
    <div className="field-footnote"><span>.md · máx. 400 kB</span><span>Hasta 100.000 caracteres</span></div>
    {error && <p className="field-error" role="alert" id={errorId}><Icon name="alert" />{error}</p>}
  </section>;
}
