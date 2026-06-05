// @vitest-environment jsdom
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  getSystemTheme,
  applyTheme,
  getCurrentTheme,
  initTheme,
  toggleTheme,
} from '../theme';

function mockMatchMedia(matches) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: vi.fn().mockReturnValue({ matches }),
  });
}

describe('getSystemTheme', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns light when system prefers light', () => {
    mockMatchMedia(true);
    expect(getSystemTheme()).toBe('light');
  });

  it('returns dark when system prefers dark', () => {
    mockMatchMedia(false);
    expect(getSystemTheme()).toBe('dark');
  });

  it('falls back to dark when matchMedia throws', () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      configurable: true,
      value: vi.fn().mockImplementation(() => {
        throw new Error('not available');
      }),
    });
    expect(getSystemTheme()).toBe('dark');
  });
});

describe('applyTheme', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sets data-theme attribute on document element', () => {
    applyTheme('light');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('persists theme preference to localStorage', () => {
    applyTheme('dark');
    expect(localStorage.getItem('walkabout_theme')).toBe('dark');
  });

  it('resolves system theme when theme is "system"', () => {
    mockMatchMedia(true);
    applyTheme('system');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    expect(localStorage.getItem('walkabout_theme')).toBe('system');
  });

  it('does not throw when localStorage is unavailable', () => {
    vi.spyOn(localStorage, 'setItem').mockImplementation(() => {
      throw new Error('quota exceeded');
    });
    expect(() => applyTheme('dark')).not.toThrow();
  });
});

describe('getCurrentTheme', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('reads saved theme from localStorage', () => {
    localStorage.setItem('walkabout_theme', 'light');
    expect(getCurrentTheme()).toBe('light');
  });

  it('returns dark as default when nothing saved', () => {
    expect(getCurrentTheme()).toBe('dark');
  });

  it('returns dark when localStorage throws', () => {
    vi.spyOn(localStorage, 'getItem').mockImplementation(() => {
      throw new Error('not available');
    });
    expect(getCurrentTheme()).toBe('dark');
  });
});

describe('initTheme', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
  });

  it('applies theme from settings parameter', () => {
    initTheme('light');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('falls back to current saved theme when no settings param', () => {
    localStorage.setItem('walkabout_theme', 'dark');
    initTheme(null);
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('falls back to dark when nothing provided', () => {
    initTheme(undefined);
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });
});

describe('toggleTheme', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('toggles from dark to light', () => {
    document.documentElement.setAttribute('data-theme', 'dark');
    const result = toggleTheme();
    expect(result).toBe('light');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('toggles from light to dark', () => {
    document.documentElement.setAttribute('data-theme', 'light');
    const result = toggleTheme();
    expect(result).toBe('dark');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('returns dark as fallback when something goes wrong', () => {
    vi.spyOn(document.documentElement, 'getAttribute').mockImplementation(() => {
      throw new Error('DOM error');
    });
    expect(toggleTheme()).toBe('dark');
  });

  it('persists toggled theme in localStorage', () => {
    document.documentElement.setAttribute('data-theme', 'dark');
    toggleTheme(); // dark → light
    expect(localStorage.getItem('walkabout_theme')).toBe('light');
  });
});

// ── Bug regression: toolbar toggle vs API config override ──────────

describe('theme persistence across page navigation (B7 regression)', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
    vi.restoreAllMocks();
  });

  it('toolbar toggle survives initTheme() with same value', () => {
    // User starts with dark theme
    applyTheme('dark');
    // User toggles to light via toolbar button
    toggleTheme(); // dark → light
    // User returns from Settings — EditorPage re-mounts,
    // API returns the correct theme (light, because it was saved)
    initTheme('light');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    expect(localStorage.getItem('walkabout_theme')).toBe('light');
  });

  it('toolbar toggle persists correctly when API has up-to-date value (post-fix)', () => {
    // After the fix: handleToggleTheme() now saves to API via
    // axios.post('/api/config/set', { key: 'appearance.theme', value }).
    // So on EditorPage re-mount, the API returns the correct value.

    // User starts with dark theme (synced with API)
    applyTheme('dark');
    localStorage.setItem('walkabout_theme', 'dark');
    expect(getCurrentTheme()).toBe('dark');

    // User clicks toolbar toggle → light (now also saves to API)
    const toggled = toggleTheme();
    expect(toggled).toBe('light');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    expect(localStorage.getItem('walkabout_theme')).toBe('light');

    // Now user navigates to Settings and back
    // EditorPage re-mounts → useEffect fetches API config
    // API now has 'light' because handleToggleTheme saved it
    const freshApiTheme = 'light';

    // initTheme with the API value — now correct
    initTheme(freshApiTheme);

    // Theme stays light — user's toggle preference is preserved
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    expect(getCurrentTheme()).toBe('light');
  });

  it('verify: getCurrentTheme reflects localStorage before initTheme', () => {
    // After toggle, localStorage is correct
    document.documentElement.setAttribute('data-theme', 'dark');
    toggleTheme(); // → light
    expect(getCurrentTheme()).toBe('light');
    expect(localStorage.getItem('walkabout_theme')).toBe('light');
  });

  it('initTheme with null falls back to localStorage (correct behavior)', () => {
    // If API has no theme, initTheme should fall back to localStorage
    localStorage.setItem('walkabout_theme', 'light');
    initTheme(null);
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('initTheme with undefined falls back to dark default', () => {
    initTheme(undefined);
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('theme chain: toggle → get → init with fresh API value', () => {
    // Full correct flow (after fix): toolbar toggle saves to API
    applyTheme('dark');

    // Toolbar toggle (now saves to API)
    toggleTheme(); // → light
    // Simulate API now returning light
    const freshApiTheme = 'light';

    // EditorPage re-mounts
    initTheme(freshApiTheme);

    // Theme should stay light
    expect(getCurrentTheme()).toBe('light');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });
});
