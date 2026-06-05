import { describe, it, expect, vi } from 'vitest';
import axios from 'axios';
import {
  listNotes,
  getNote,
  saveNote,
  createNote,
  deleteNote,
  executeNote,
  getEnvInfo,
  installPackages,
  saveExport,
} from '../api';

vi.mock('axios');

describe('listNotes', () => {
  it('fetches notes list from API', async () => {
    const data = [{ name: 'note1.py' }, { name: 'note2.py' }];
    axios.get.mockResolvedValueOnce({ data });

    const result = await listNotes();
    expect(result).toEqual(data);
    expect(axios.get).toHaveBeenCalledWith('/api/notes');
  });
});

describe('getNote', () => {
  it('fetches a single note by path', async () => {
    const note = { name: 'test.py', content: 'print(1)' };
    axios.get.mockResolvedValueOnce({ data: note });

    const result = await getNote('test.py');
    expect(result).toEqual(note);
    expect(axios.get).toHaveBeenCalledWith('/api/notes/test.py');
  });

  it('URL-encodes special characters in path', async () => {
    axios.get.mockResolvedValueOnce({ data: {} });
    await getNote('sub/test.py');
    expect(axios.get).toHaveBeenCalledWith(
      expect.stringContaining('sub%2Ftest.py')
    );
  });
});

describe('saveNote', () => {
  it('sends PUT request with content', async () => {
    axios.put.mockResolvedValueOnce({});
    await saveNote('note.py', 'x = 1');
    expect(axios.put).toHaveBeenCalledWith(
      expect.stringContaining('note.py'),
      { content: 'x = 1' }
    );
  });
});

describe('createNote', () => {
  it('sends POST with name', async () => {
    const response = { path: 'new_note.py' };
    axios.post.mockResolvedValueOnce({ data: response });

    const result = await createNote('new_note.py');
    expect(result).toEqual(response);
    expect(axios.post).toHaveBeenCalledWith(
      '/api/notes',
      { name: 'new_note.py' }
    );
  });
});

describe('deleteNote', () => {
  it('sends DELETE request', async () => {
    axios.delete.mockResolvedValueOnce({});
    await deleteNote('old.py');
    expect(axios.delete).toHaveBeenCalledWith(
      expect.stringContaining('old.py')
    );
  });
});

describe('executeNote', () => {
  it('sends execute request with path and content', async () => {
    const trace = { steps: [], files: {} };
    axios.post.mockResolvedValueOnce({ data: trace });

    const result = await executeNote('run.py', 'x = 1');
    expect(result).toEqual(trace);
    expect(axios.post).toHaveBeenCalledWith(
      '/api/execute',
      { path: 'run.py', content: 'x = 1' }
    );
  });
});

describe('getEnvInfo', () => {
  it('fetches environment info', async () => {
    const env = { python: '3.11', packages: ['numpy'] };
    axios.get.mockResolvedValueOnce({ data: env });

    const result = await getEnvInfo();
    expect(result).toEqual(env);
    expect(axios.get).toHaveBeenCalledWith('/api/env');
  });
});

describe('installPackages', () => {
  it('sends install request with package list', async () => {
    const result = { ok: true, packages: ['numpy'] };
    axios.post.mockResolvedValueOnce({ data: result });

    const res = await installPackages(['numpy']);
    expect(res).toEqual(result);
    expect(axios.post).toHaveBeenCalledWith(
      '/api/env/install',
      { packages: ['numpy'] }
    );
  });
});

describe('saveExport', () => {
  it('sends save export request', async () => {
    const result = { path: '/tmp/out.html' };
    axios.post.mockResolvedValueOnce({ data: result });

    const res = await saveExport('note.py');
    expect(res).toEqual(result);
    expect(axios.post).toHaveBeenCalledWith(
      '/api/export/save',
      { path: 'note.py' }
    );
  });
});
