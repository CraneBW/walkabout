import axios from 'axios';

export async function listNotes() {
  const res = await axios.get('/api/notes');
  return res.data;
}

export async function getNote(path) {
  const res = await axios.get(`/api/notes/${encodeURIComponent(path)}`);
  return res.data;
}

export async function saveNote(path, content) {
  await axios.put(`/api/notes/${encodeURIComponent(path)}`, { content });
}

export async function createNote(name) {
  const res = await axios.post('/api/notes', { name });
  return res.data;
}

export async function deleteNote(path) {
  await axios.delete(`/api/notes/${encodeURIComponent(path)}`);
}

export async function executeNote(path, content) {
  const res = await axios.post('/api/execute', { path, content });
  return res.data;
}

export async function getEnvInfo() {
  const res = await axios.get('/api/env');
  return res.data;
}

export async function installPackages(packages) {
  const res = await axios.post('/api/env/install', { packages });
  return res.data;
}

export async function exportNote(path, content) {
  const res = await axios.post('/api/export', { path, content }, {
    responseType: 'blob',
  });
  // Trigger download
  const url = window.URL.createObjectURL(new Blob([res.data]));
  const link = document.createElement('a');
  link.href = url;
  const disposition = res.headers['content-disposition'];
  const match = disposition && disposition.match(/filename="?(.+?)"?$/);
  link.download = match ? match[1] : 'walkthrough.html';
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
  return res;
}
