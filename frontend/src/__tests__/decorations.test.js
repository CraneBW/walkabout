// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest';
import { computeEnv, computeDecorations } from '../utils';

// ----------------------------------------------------------------------
// computeEnv — merge env from current step and prior steps in same frame
// ----------------------------------------------------------------------
describe('computeEnv', () => {
  it('returns env for the current step', () => {
    const trace = {
      steps: [
        { stack: [{ path: 'a.py', line_number: 1 }], env: { x: 1 } },
      ],
    };
    expect(computeEnv(trace, 0)).toEqual({ x: 1 });
  });

  it('merges env from prior steps in the same stack frame', () => {
    const trace = {
      steps: [
        { stack: [{ path: 'a.py', line_number: 1 }], env: { x: 1 } },
        { stack: [{ path: 'a.py', line_number: 2 }], env: { y: 2 } },
      ],
    };
    // step 1 should include x (set in step 0) and y (set in step 1)
    expect(computeEnv(trace, 1)).toEqual({ x: 1, y: 2 });
  });

  it('later values overwrite earlier ones in the same frame', () => {
    const trace = {
      steps: [
        { stack: [{ path: 'a.py', line_number: 1 }], env: { x: 1 } },
        { stack: [{ path: 'a.py', line_number: 2 }], env: { x: 99 } },
      ],
    };
    expect(computeEnv(trace, 1)).toEqual({ x: 99 });
  });

  it('does NOT merge env from a different stack frame (ancestor)', () => {
    const trace = {
      steps: [
        { stack: [{ path: 'a.py', line_number: 1 }], env: { x: 1 } },
        { stack: [{ path: 'a.py', line_number: 2 }, { path: 'a.py', line_number: 10 }], env: { y: 2 } },
      ],
    };
    // step 1 is a different frame (longer stack), so x should NOT be merged
    const env = computeEnv(trace, 1);
    expect(env).not.toHaveProperty('x');
    expect(env).toEqual({ y: 2 });
  });

  it('returns empty object when no env vars exist in the current frame', () => {
    const trace = {
      steps: [
        { stack: [{ path: 'a.py', line_number: 1 }], env: {} },
      ],
    };
    expect(computeEnv(trace, 0)).toEqual({});
  });

  it('returns empty object for first step with empty env', () => {
    const trace = {
      steps: [
        { stack: [{ path: 'a.py', line_number: 1 }], env: {} },
        { stack: [{ path: 'a.py', line_number: 2 }], env: { y: 2 } },
      ],
    };
    // step 0 has empty env, should still be empty (no prior steps in frame)
    expect(computeEnv(trace, 0)).toEqual({});
  });

  it('handles null/undefined env gracefully', () => {
    const trace = {
      steps: [
        { stack: [{ path: 'a.py', line_number: 1 }], env: null },
      ],
    };
    expect(computeEnv(trace, 0)).toEqual({});
  });
});

// ----------------------------------------------------------------------
// computeDecorations — map env object to per-line decoration objects
// ----------------------------------------------------------------------
describe('computeDecorations', () => {
  it('maps each env variable to the source line where it appears', () => {
    const env = { x: 42, y: 'hello' };
    const source = 'x = 1\ny = "hello"\nz = 3';
    const decos = computeDecorations(env, source);
    expect(decos).toEqual(
      expect.arrayContaining([
        { line: 1, text: 'x = 42' },
        { line: 2, text: 'y = "hello"' },
      ]),
    );
  });

  it('returns empty array for empty env', () => {
    expect(computeDecorations({}, 'x = 1')).toEqual([]);
  });

  it('skips variables that cannot be found in the source', () => {
    const env = { nonexistent: 42 };
    const source = 'x = 1\ny = 2';
    const decos = computeDecorations(env, source);
    expect(decos).toEqual([]);
  });

  it('handles multiline source', () => {
    const env = { x: 10 };
    const source = 'a = 1\nb = 2\nx = 3\nd = 4';
    const decos = computeDecorations(env, source);
    expect(decos).toEqual([{ line: 3, text: 'x = 10' }]);
  });

  it('finds the last assignment line for a variable when used multiple times', () => {
    const env = { x: 99 };
    // x appears on lines 1 and 3; the last one (line 3) should be chosen
    const source = 'x = 1\ny = 2\nx = 3';
    const decos = computeDecorations(env, source);
    expect(decos).toEqual([{ line: 3, text: 'x = 99' }]);
  });

  it('renders string values with JSON.stringify', () => {
    const env = { msg: 'hello world' };
    const source = 'msg = "hi"';
    const decos = computeDecorations(env, source);
    expect(decos).toEqual([{ line: 1, text: 'msg = "hello world"' }]);
  });

  it('renders number values inline', () => {
    const env = { n: 42 };
    const source = 'n = 0';
    const decos = computeDecorations(env, source);
    expect(decos).toEqual([{ line: 1, text: 'n = 42' }]);
  });

  it('renders complex values (list, dict) as JSON', () => {
    const env = { items: [1, 2, 3] };
    const source = 'items = []';
    const decos = computeDecorations(env, source);
    expect(decos).toEqual([{ line: 1, text: 'items = [1,2,3]' }]);
  });
});
