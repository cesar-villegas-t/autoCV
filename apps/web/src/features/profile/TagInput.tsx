import { useState, type KeyboardEvent } from 'react';
import { Icon } from '../../components/Icon';

interface Props {
  id: string;
  values: string[];
  onChange: (values: string[]) => void;
  max: number;
  placeholder?: string;
}

/** A small chip editor for short free-text lists, such as cities open to relocation. */
export function TagInput({ id, values, onChange, max, placeholder }: Props) {
  const [draft, setDraft] = useState('');

  function commit() {
    const value = draft.trim();
    setDraft('');
    if (value && values.length < max && !values.includes(value)) onChange([...values, value]);
  }
  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter' || event.key === ',') { event.preventDefault(); commit(); }
    else if (event.key === 'Backspace' && !draft && values.length) onChange(values.slice(0, -1));
  }

  return <div className="tag-input">
    {values.map((value, index) => (
      <span className="tag" key={value}>
        {value}
        <button type="button" aria-label={`Quitar ${value}`} onClick={() => onChange(values.filter((_, i) => i !== index))}>
          <Icon name="close" />
        </button>
      </span>
    ))}
    {values.length < max && <input id={id} value={draft} placeholder={values.length ? '' : placeholder}
      onChange={event => setDraft(event.target.value)} onKeyDown={onKeyDown} onBlur={commit} />}
  </div>;
}
