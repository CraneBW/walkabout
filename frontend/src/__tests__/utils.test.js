import { describe, it, expect, vi } from 'vitest';
import { navigateToUrl, getLast } from '../utils';

describe('getLast', () => {
  it('returns the last element of an array', () => {
    expect(getLast([1, 2, 3])).toBe(3);
  });

  it('returns the only element for single-element arrays', () => {
    expect(getLast([42])).toBe(42);
  });

  it('returns undefined for empty array', () => {
    expect(getLast([])).toBeUndefined();
  });

  it('works with string arrays', () => {
    expect(getLast(['a', 'b', 'c'])).toBe('c');
  });

  it('works with mixed arrays', () => {
    expect(getLast([null, 'hello', 7])).toBe(7);
  });
});

describe('navigateToUrl', () => {
  it('adds new URL params and calls navigate', () => {
    const urlParams = new URLSearchParams('');
    const navigate = vi.fn();
    const location = { pathname: '/editor' };

    navigateToUrl(urlParams, { foo: 'bar' }, location, navigate);

    expect(navigate).toHaveBeenCalledTimes(1);
    const arg = navigate.mock.calls[0][0];
    expect(arg.pathname).toBe('/editor');
    expect(arg.search).toContain('foo=bar');
  });

  it('removes params when delta value is null', () => {
    const urlParams = new URLSearchParams('?keep=yes&remove=yes');
    const navigate = vi.fn();
    const location = { pathname: '/view' };

    navigateToUrl(urlParams, { remove: null }, location, navigate);

    expect(navigate).toHaveBeenCalledTimes(1);
    const arg = navigate.mock.calls[0][0];
    expect(arg.search).toContain('keep=yes');
    expect(arg.search).not.toContain('remove');
  });

  it('removes params when delta value is false', () => {
    const urlParams = new URLSearchParams('?flag=true');
    const navigate = vi.fn();
    const location = { pathname: '/' };

    navigateToUrl(urlParams, { flag: false }, location, navigate);

    expect(navigate).toHaveBeenCalledTimes(1);
    const arg = navigate.mock.calls[0][0];
    expect(arg.search).not.toContain('flag');
  });

  it('handles multiple params at once', () => {
    const urlParams = new URLSearchParams('');
    const navigate = vi.fn();
    const location = { pathname: '/editor' };

    navigateToUrl(urlParams, { a: '1', b: '2', c: null }, location, navigate);

    const arg = navigate.mock.calls[0][0];
    expect(arg.search).toContain('a=1');
    expect(arg.search).toContain('b=2');
    expect(arg.search).not.toContain('c');
  });
});
