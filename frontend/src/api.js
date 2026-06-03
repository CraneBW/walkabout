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

export async function exportNote(path) {
  // Browser-native download: navigate to GET endpoint
  window.location.href = `/api/export?path=${encodeURIComponent(path)}`;
}
