import type { ReactNode } from 'react';
import { Icon } from '../../components/Icon';

interface Props<T> {
  items: T[];
  onChange: (items: T[]) => void;
  empty: T;
  max: number;
  addLabel: string;
  itemLabel: (item: T, index: number) => string;
  children: (item: T, update: (patch: Partial<T>) => void, index: number) => ReactNode;
}

/** Add, remove and reorder chrome shared by every repeatable profile section. */
export function BlockList<T extends object>({ items, onChange, empty, max, addLabel, itemLabel, children }: Props<T>) {
  function update(index: number, patch: Partial<T>) {
    onChange(items.map((item, i) => (i === index ? { ...item, ...patch } : item)));
  }
  function move(index: number, delta: number) {
    const target = index + delta;
    if (target < 0 || target >= items.length) return;
    const next = items.slice();
    [next[index], next[target]] = [next[target]!, next[index]!];
    onChange(next);
  }

  return <div className="block-list">
    {items.map((item, index) => {
      const label = itemLabel(item, index);
      return <div className="block-card" key={index}>
        <div className="block-card-header">
          <strong>{label}</strong>
          <div className="block-card-actions">
            <button type="button" disabled={index === 0} onClick={() => move(index, -1)} aria-label={`Subir ${label}`}>
              <Icon name="up" />
            </button>
            <button type="button" disabled={index === items.length - 1} onClick={() => move(index, 1)} aria-label={`Bajar ${label}`}>
              <Icon name="down" />
            </button>
            <button type="button" className="remove-block-button" aria-label={`Eliminar ${label}`}
              onClick={() => onChange(items.filter((_, i) => i !== index))}>
              <Icon name="trash" />
            </button>
          </div>
        </div>
        {children(item, patch => update(index, patch), index)}
      </div>;
    })}
    <button type="button" className="add-block-button" disabled={items.length >= max}
      onClick={() => onChange([...items, { ...empty }])}>
      <Icon name="plus" />{addLabel}
    </button>
  </div>;
}
