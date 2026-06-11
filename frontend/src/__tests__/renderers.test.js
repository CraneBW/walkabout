import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import { getRenderers } from '../api';

vi.mock('axios');

describe('getRenderers API call', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('returns expected renderer data from API', async () => {
    const mockData = {
      vega: { type: 'vega', frontend_js: 'https://cdn.jsdelivr.net/npm/vega-embed' },
      mermaid: { type: 'mermaid', frontend_js: '/static/mermaid.js' },
    };
    axios.get.mockResolvedValueOnce({ data: mockData });

    const result = await getRenderers();
    expect(result).toEqual(mockData);
    expect(axios.get).toHaveBeenCalledWith('/api/renderers');
  });

  it('returns empty object when no renderers registered', async () => {
    axios.get.mockResolvedValueOnce({ data: {} });

    const result = await getRenderers();
    expect(result).toEqual({});
  });

  it('test_getRenderers_returns_empty_on_error', async () => {
    axios.get.mockRejectedValueOnce(new Error('Network error'));

    const result = await getRenderers();
    expect(result).toEqual({});
  });
});

describe('renderRendering with registry pattern', () => {
  /**
   * Test the renderRendering registry pattern by reimplementing
   * the logic from TraceViewer as a pure function.
   */
  function renderRendering(rendering, customRenderers = {}) {
    const type = rendering.type || 'text';
    const data = rendering.data || '';
    const style = rendering.style || {};

    // Built-in types (hardcoded)
    if (type === 'markdown') {
      return { kind: 'markdown', data, style };
    }
    if (type === 'image') {
      return { kind: 'image', data, style };
    }
    if (type === 'link') {
      return { kind: 'link', data, style };
    }

    // Custom renderers (from registry)
    if (customRenderers[type]) {
      return { kind: 'custom', type, data, style, meta: customRenderers[type] };
    }

    // Fallback: display data as text
    return { kind: 'text', data, style };
  }

  it('dispatches markdown to built-in handler', () => {
    const result = renderRendering({ type: 'markdown', data: '# Hello' });
    expect(result.kind).toBe('markdown');
  });

  it('dispatches image to built-in handler', () => {
    const result = renderRendering({ type: 'image', data: 'https://example.com/img.png' });
    expect(result.kind).toBe('image');
  });

  it('dispatches link to built-in handler', () => {
    const result = renderRendering({ type: 'link', data: 'Click here' });
    expect(result.kind).toBe('link');
  });

  it('falls back to text for unknown type', () => {
    const result = renderRendering({ type: 'unknown_type', data: 'some data' });
    expect(result.kind).toBe('text');
  });

  it('uses custom renderer when type matches registry', () => {
    const customRenderers = {
      vega: { type: 'vega', frontend_js: '/vega.js' },
    };
    const result = renderRendering(
      { type: 'vega', data: '{"x": 1}' },
      customRenderers,
    );
    expect(result.kind).toBe('custom');
    expect(result.type).toBe('vega');
    expect(result.meta.frontend_js).toBe('/vega.js');
  });

  it('custom renderer overrides unknown type behavior', () => {
    // Without registry, 'chart' falls back to text
    expect(renderRendering({ type: 'chart', data: 'x' }).kind).toBe('text');

    // With registry, 'chart' dispatches to custom
    const customRenderers = {
      chart: { type: 'chart', frontend_js: '/chart.js' },
    };
    expect(
      renderRendering({ type: 'chart', data: 'x' }, customRenderers).kind,
    ).toBe('custom');
  });

  it('renders rendering with no type as text fallback', () => {
    const result = renderRendering({ data: 'raw data' });
    expect(result.kind).toBe('text');
  });

  it('rendering with no data at all', () => {
    const result = renderRendering({ type: 'markdown' });
    expect(result.data).toBe('');
  });

  it('test_custom_renderer_overrides_fallback', () => {
    const customRenderers = {
      chart: { type: 'chart', frontend_js: '/chart.js' },
    };
    // Without custom renderer, chart falls back to text
    expect(renderRendering({ type: 'chart', data: 'x' }).kind).toBe('text');
    // With custom renderer, chart dispatches to custom handler
    expect(
      renderRendering({ type: 'chart', data: 'x' }, customRenderers).kind,
    ).toBe('custom');
  });

  it('test_custom_renderer_receives_rendering_data', () => {
    const customRenderers = {
      vega: { type: 'vega', frontend_js: '/vega.js' },
    };
    const rendering = { type: 'vega', data: '{"x": 1}', style: { color: 'red' } };
    const result = renderRendering(rendering, customRenderers);
    expect(result.kind).toBe('custom');
    expect(result.type).toBe('vega');
    expect(result.data).toBe('{"x": 1}');
    expect(result.style).toEqual({ color: 'red' });
    expect(result.meta).toEqual({ type: 'vega', frontend_js: '/vega.js' });
  });
});
