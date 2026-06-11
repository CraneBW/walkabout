// @vitest-environment jsdom
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import React from 'react';
import axios from 'axios';

vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import TraceViewer, {
  updateUrlParams,
  stepForward,
  stepBackward,
  toggleRawMode,
  toggleAnimateMode,
} from '../TraceViewer';

// Helper to change the current URL in jsdom
function setUrl(href) {
  window.history.pushState({}, '', href);
}

// ---------------------------------------------------------------------------
// updateUrlParams
// ---------------------------------------------------------------------------
describe('updateUrlParams', () => {
  beforeEach(() => {
    setUrl('/');
    vi.spyOn(window.history, 'pushState');
    vi.spyOn(window, 'dispatchEvent');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sets a new param in the URL', () => {
    updateUrlParams({ step: 5 });
    expect(window.history.pushState).toHaveBeenCalledWith(
      {}, '', expect.stringContaining('step=5'),
    );
  });

  it('removes a param when value is null', () => {
    setUrl('?source=test.py&step=2');
    updateUrlParams({ source: null });
    // Use last call since setUrl() in test body is also tracked by spy
    const calls = window.history.pushState.mock.calls;
    const url = calls[calls.length - 1][2];
    expect(url).not.toContain('source');
  });

  it('preserves existing params not mentioned in the delta', () => {
    setUrl('?trace=test.json&step=2');
    updateUrlParams({ source: 'main.py' });
    const calls = window.history.pushState.mock.calls;
    const url = calls[calls.length - 1][2];
    expect(url).toContain('trace=test.json');
    expect(url).toContain('step=2');
    expect(url).toContain('source=main.py');
  });

  it('dispatches a popstate event after pushState', () => {
    updateUrlParams({ step: 1 });
    expect(window.dispatchEvent).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'popstate' }),
    );
  });
});

// ---------------------------------------------------------------------------
// stepForward
// ---------------------------------------------------------------------------
describe('stepForward', () => {
  beforeEach(() => {
    setUrl('/');
    vi.spyOn(window.history, 'pushState');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('when at step 0 with 5 steps, updates step to 1', () => {
    stepForward({ trace: { steps: [1, 2, 3, 4, 5] }, currentStepIndex: 0 });
    expect(window.history.pushState).toHaveBeenCalledWith(
      {}, '', expect.stringContaining('step=1'),
    );
  });

  it('when at last step, does nothing', () => {
    stepForward({ trace: { steps: [1, 2, 3, 4, 5] }, currentStepIndex: 4 });
    expect(window.history.pushState).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// stepBackward
// ---------------------------------------------------------------------------
describe('stepBackward', () => {
  beforeEach(() => {
    setUrl('/');
    vi.spyOn(window.history, 'pushState');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('when at step 2, updates step to 1', () => {
    stepBackward({ currentStepIndex: 2 });
    expect(window.history.pushState).toHaveBeenCalledWith(
      {}, '', expect.stringContaining('step=1'),
    );
  });

  it('when at step 0, does nothing', () => {
    stepBackward({ currentStepIndex: 0 });
    expect(window.history.pushState).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// toggleRawMode
// ---------------------------------------------------------------------------
describe('toggleRawMode', () => {
  beforeEach(() => {
    setUrl('/');
    vi.spyOn(window.history, 'pushState');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('when rawMode=false, sets raw=1', () => {
    toggleRawMode({ rawMode: false });
    expect(window.history.pushState).toHaveBeenCalledWith(
      {}, '', expect.stringContaining('raw=1'),
    );
  });

  it('when rawMode=true, removes raw param', () => {
    setUrl('?raw=1');
    toggleRawMode({ rawMode: true });
    const calls = window.history.pushState.mock.calls;
    const url = calls[calls.length - 1][2];
    expect(url).not.toContain('raw');
  });
});

// ---------------------------------------------------------------------------
// toggleAnimateMode
// ---------------------------------------------------------------------------
describe('toggleAnimateMode', () => {
  beforeEach(() => {
    setUrl('/');
    vi.spyOn(window.history, 'pushState');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('when animateMode=false, sets animate=1', () => {
    toggleAnimateMode({ animateMode: false });
    expect(window.history.pushState).toHaveBeenCalledWith(
      {}, '', expect.stringContaining('animate=1'),
    );
  });

  it('when animateMode=true, removes animate param', () => {
    setUrl('?animate=1');
    toggleAnimateMode({ animateMode: true });
    const calls = window.history.pushState.mock.calls;
    const url = calls[calls.length - 1][2];
    expect(url).not.toContain('animate');
  });
});

// ---------------------------------------------------------------------------
// TraceViewer component (URL reads from window.location.search)
// ---------------------------------------------------------------------------
describe('TraceViewer component - URL reading', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows "No trace path provided" when no trace param in URL', () => {
    setUrl('/');
    render(<TraceViewer />);
    expect(screen.getByText('No trace path provided')).toBeInTheDocument();
  });

  it('does not show no-trace message when trace param is present', () => {
    setUrl('/?trace=test.json');
    render(<TraceViewer />);
    expect(screen.queryByText('No trace path provided')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// updateUrlParams — additional tests
// ---------------------------------------------------------------------------
describe('updateUrlParams - additional', () => {
  beforeEach(() => {
    setUrl('/');
    vi.spyOn(window.history, 'pushState');
    vi.spyOn(window, 'dispatchEvent');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('test_updateUrlParams_preserves_other_params', () => {
    setUrl('?trace=foo&raw=1');
    updateUrlParams({ step: 5 });
    const calls = window.history.pushState.mock.calls;
    const url = calls[calls.length - 1][2];
    expect(url).toContain('trace=foo');
    expect(url).toContain('raw=1');
    expect(url).toContain('step=5');
  });
});

// ---------------------------------------------------------------------------
// stepForward — additional tests
// ---------------------------------------------------------------------------
describe('stepForward - additional', () => {
  beforeEach(() => {
    setUrl('/');
    vi.spyOn(window.history, 'pushState');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('test_step_forward_at_last_step_noop', () => {
    stepForward({ trace: { steps: [1, 2, 3, 4, 5] }, currentStepIndex: 4 });
    expect(window.history.pushState).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// TraceViewer component — rendering dispatch
// ---------------------------------------------------------------------------
describe('TraceViewer component - rendering dispatch', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // jsdom does not implement scrollIntoView
    Element.prototype.scrollIntoView = vi.fn();
  });

  it('test_custom_renderer_fallback', async () => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/api/renderers')) return Promise.resolve({ data: {} });
      return Promise.resolve({
        data: {
          files: { 'test.py': 'x = 1\ny = 2\nz = 3' },
          steps: [{
            stack: [{ path: 'test.py', line_number: 1 }],
            env: {},
            renderings: [{ type: 'unknown_type', data: 'fallback data here' }],
          }],
        },
      });
    });
    setUrl('/?trace=/api/traces/test.json');
    render(<TraceViewer />);
    await waitFor(() => {
      expect(screen.getByText('fallback data here')).toBeInTheDocument();
    });
  });

  it('test_builtin_markdown_renderer', async () => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/api/renderers')) return Promise.resolve({ data: {} });
      return Promise.resolve({
        data: {
          files: { 'test.py': 'x = 1\ny = 2\nz = 3' },
          steps: [{
            stack: [{ path: 'test.py', line_number: 1 }],
            env: {},
            renderings: [{ type: 'markdown', data: '**bold text**' }],
          }],
        },
      });
    });
    setUrl('/?trace=/api/traces/test.json');
    render(<TraceViewer />);
    await waitFor(() => {
      expect(screen.getByText('bold text')).toBeInTheDocument();
    });
  });

  it('test_builtin_image_renderer', async () => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/api/renderers')) return Promise.resolve({ data: {} });
      return Promise.resolve({
        data: {
          files: { 'test.py': 'x = 1\ny = 2\nz = 3' },
          steps: [{
            stack: [{ path: 'test.py', line_number: 1 }],
            env: {},
            renderings: [{ type: 'image', data: 'https://example.com/img.png' }],
          }],
        },
      });
    });
    setUrl('/?trace=/api/traces/test.json');
    const { container } = render(<TraceViewer />);
    await waitFor(() => {
      expect(container.querySelector('img')).toBeInTheDocument();
    });
    expect(container.querySelector('img')).toHaveAttribute('src', 'https://example.com/img.png');
  });

  it('test_builtin_link_renderer_external', async () => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/api/renderers')) return Promise.resolve({ data: {} });
      return Promise.resolve({
        data: {
          files: { 'test.py': 'x = 1\ny = 2\nz = 3' },
          steps: [{
            stack: [{ path: 'test.py', line_number: 1 }],
            env: {},
            renderings: [{
              type: 'link',
              data: 'Click here',
              external_link: { url: 'https://example.com', title: 'Example Site' },
            }],
          }],
        },
      });
    });
    setUrl('/?trace=/api/traces/test.json');
    render(<TraceViewer />);
    await waitFor(() => {
      expect(screen.getByRole('link', { name: 'Example Site' })).toBeInTheDocument();
    });
    const link = screen.getByRole('link', { name: 'Example Site' });
    expect(link).toHaveAttribute('href', 'https://example.com');
    expect(link).toHaveAttribute('target', '_blank');
  });
});
