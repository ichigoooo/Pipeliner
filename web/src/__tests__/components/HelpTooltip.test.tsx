import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { HelpTooltip } from '@/components/ui/HelpTooltip';

describe('HelpTooltip', () => {
  it('shows content on hover, focus, and click', () => {
    render(<HelpTooltip content="Detailed guidance" label="Section help" />);

    const button = screen.getByRole('button', { name: 'Section help' });

    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();

    fireEvent.mouseEnter(button);
    expect(screen.getByRole('tooltip')).toHaveTextContent('Detailed guidance');

    fireEvent.mouseLeave(button.parentElement as HTMLElement);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();

    fireEvent.focus(button);
    expect(screen.getByRole('tooltip')).toHaveTextContent('Detailed guidance');

    fireEvent.blur(button);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();

    fireEvent.click(button);
    expect(screen.getByRole('tooltip')).toHaveTextContent('Detailed guidance');

    fireEvent.pointerDown(document.body);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });
});
