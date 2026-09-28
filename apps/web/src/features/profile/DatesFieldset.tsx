interface Props {
  start: string | null;
  end: string | null;
  current: boolean;
  onChange: (patch: { start_date?: string | null; end_date?: string | null; current?: boolean }) => void;
  error: (field: 'start_date' | 'end_date' | 'current') => string | undefined;
  startRequired?: boolean;
  currentLabel?: string;
}

/** A start/end month pair with an "ongoing" checkbox, shared by every dated profile block. */
export function DatesFieldset({ start, end, current, onChange, error, startRequired, currentLabel = 'Actualmente' }: Props) {
  return <div className="dates-fieldset">
    <label className="form-field">
      <span>Inicio</span>
      <input type="month" required={startRequired} value={start ?? ''}
        onChange={event => onChange({ start_date: event.target.value || (startRequired ? '' : null) })} />
      {error('start_date') && <p className="field-error" role="alert">{error('start_date')}</p>}
    </label>
    <label className="form-field">
      <span>Fin</span>
      <input type="month" value={end ?? ''} disabled={current}
        onChange={event => onChange({ end_date: event.target.value || null })} />
      {error('end_date') && <p className="field-error" role="alert">{error('end_date')}</p>}
    </label>
    <label className="checkbox-field">
      <input type="checkbox" checked={current}
        onChange={event => onChange({ current: event.target.checked, end_date: event.target.checked ? null : end })} />
      {currentLabel}
    </label>
  </div>;
}
