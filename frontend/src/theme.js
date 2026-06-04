const THEME_KEY = 'walkabout_theme';

export function getSystemTheme() {
  if (window.matchMedia('(prefers-color-scheme: light)').matches) return 'light';
  return 'dark';
}

export function applyTheme(theme) {
  const resolved = theme === 'system' ? getSystemTheme() : theme;
  document.documentElement.setAttribute('data-theme', resolved);
  localStorage.setItem(THEME_KEY, theme);
}

export function getCurrentTheme() {
  return localStorage.getItem(THEME_KEY) || 'dark';
}

export function initTheme(settingsTheme) {
  const theme = settingsTheme || getCurrentTheme();
  applyTheme(theme);
}

export function toggleTheme() {
  const resolved = document.documentElement.getAttribute('data-theme');
  const next = resolved === 'light' ? 'dark' : 'light';
  applyTheme(next);
  return next;
}
