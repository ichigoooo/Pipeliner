import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { TabList } from '@/components/ui/TabList';

describe('TabList', () => {
  it('renders tabs and handles clicks', () => {
    const mockOnTabChange = vi.fn();
    const tabs = ['Tab 1', 'Tab 2'];
    
    render(
      <TabList tabs={tabs} activeTab="Tab 1" onTabChange={mockOnTabChange} />
    );
    
    expect(screen.getByText('Tab 1')).toHaveClass('border-amber-500');
    expect(screen.getByText('Tab 2')).toHaveClass('border-transparent');
    
    fireEvent.click(screen.getByText('Tab 2'));
    expect(mockOnTabChange).toHaveBeenCalledWith('Tab 2');
  });
});
