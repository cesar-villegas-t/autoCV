import { act, renderHook, waitFor } from '@testing-library/react';
import { expect, it, vi, afterEach } from 'vitest';
import { useMarkdownFile } from './useMarkdownFile';
import * as validation from './fileValidation';

afterEach(() => vi.restoreAllMocks());

it('ignores a stale read when a newer file has been selected', async () => {
  let complete!: (file: validation.MarkdownFile) => void;
  vi.spyOn(validation, 'validateMarkdown')
    .mockImplementationOnce(() => new Promise(resolve => { complete = resolve; }))
    .mockResolvedValueOnce({ name: 'new.md', size: 4, content: 'new' });
  const { result } = renderHook(() => useMarkdownFile());
  let pending!: Promise<void>;
  act(() => { pending = result.current.select([new File(['old'], 'old.md')]); });
  expect(result.current.reading).toBe(true);
  expect(result.current.valid).toBe(false);
  await act(() => result.current.select([new File(['new'], 'new.md')]));
  await act(async () => { complete({name:'old.md',size:3,content:'old'}); await pending; });
  expect(result.current.file?.name).toBe('new.md');
  expect(result.current.valid).toBe(true);
});

it('does not restore a file after it is removed during reading', async () => {
  let complete!: (file: validation.MarkdownFile) => void;
  vi.spyOn(validation, 'validateMarkdown').mockImplementation(() => new Promise(resolve => { complete = resolve; }));
  const {result} = renderHook(() => useMarkdownFile());
  let pending!: Promise<void>;
  act(() => { pending = result.current.select([new File(['old'], 'old.md')]); });
  act(() => result.current.remove());
  await act(async () => { complete({name:'old.md',size:3,content:'old'}); await pending; });
  await waitFor(() => expect(result.current.file).toBeNull());
  expect(result.current.reading).toBe(false);
});
