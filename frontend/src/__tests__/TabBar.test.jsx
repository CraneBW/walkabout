// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import TabBar from '../components/TabBar';

describe('TabBar', () => {
  const tabs = [
    { id: 'file1.py', path: 'file1.py', dirty: false },
    { id: 'folder/file2.py', path: 'folder/file2.py', dirty: true },
  ];

  it('renders tab labels from tabs prop', () => {
    render(<TabBar tabs={tabs} activeTabId="file1.py" onSelect={() => {}} onClose={() => {}} />);
    expect(screen.getByText('file1.py')).toBeTruthy();
    expect(screen.getByText('file2.py')).toBeTruthy();
  });

  it('highlights activeTabId with active class', () => {
    render(<TabBar tabs={tabs} activeTabId="file1.py" onSelect={() => {}} onClose={() => {}} />);
    const tabItems = screen.getAllByRole('tab');
    expect(tabItems[0].className).toContain('tab-bar-item-active');
    expect(tabItems[1].className).not.toContain('tab-bar-item-active');
  });

  it('calls onSelect when tab clicked', () => {
    const onSelect = vi.fn();
    render(<TabBar tabs={tabs} activeTabId="file1.py" onSelect={onSelect} onClose={() => {}} />);
    fireEvent.click(screen.getByText('file2.py'));
    expect(onSelect).toHaveBeenCalledWith('folder/file2.py');
  });

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn();
    const onSelect = vi.fn();
    render(<TabBar tabs={tabs} activeTabId="file1.py" onSelect={onSelect} onClose={onClose} />);
    const closeBtns = screen.getAllByText('\u00D7');
    fireEvent.click(closeBtns[0]);
    expect(onClose).toHaveBeenCalled();
  });

  it('close button click does NOT trigger onSelect (stopPropagation)', () => {
    const onSelect = vi.fn();
    const onClose = vi.fn();
    render(<TabBar tabs={tabs} activeTabId="file1.py" onSelect={onSelect} onClose={onClose} />);
    const closeBtns = screen.getAllByText('\u00D7');
    fireEvent.click(closeBtns[0]);
    expect(onSelect).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it('shows dirty indicator (*) on dirty tabs', () => {
    render(<TabBar tabs={tabs} activeTabId="file1.py" onSelect={() => {}} onClose={() => {}} />);
    expect(screen.getByText('*')).toBeTruthy();
  });

  it('dirty tabs have tab-bar-item-dirty class', () => {
    render(<TabBar tabs={tabs} activeTabId="file1.py" onSelect={() => {}} onClose={() => {}} />);
    const tabItems = screen.getAllByRole('tab');
    expect(tabItems[0].className).not.toContain('tab-bar-item-dirty');
    expect(tabItems[1].className).toContain('tab-bar-item-dirty');
  });

  it('empty tabs array renders nothing', () => {
    const { container } = render(<TabBar tabs={[]} activeTabId={null} onSelect={() => {}} onClose={() => {}} />);
    expect(container.innerHTML).toBe('');
  });

  it('single tab hides close button', () => {
    const singleTab = [{ id: 'file1.py', path: 'file1.py', dirty: false }];
    render(<TabBar tabs={singleTab} activeTabId="file1.py" onSelect={() => {}} onClose={() => {}} />);
    expect(screen.queryByText('\u00D7')).toBeNull();
  });
});
