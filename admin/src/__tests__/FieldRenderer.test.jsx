import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

afterEach(cleanup);
import FieldRenderer from '../editor/fields/FieldRenderer.jsx';
import { checkImageSize, validateField } from '../editor/validate.js';

const rec = (values) => ({ key: 'hero-slides:18', values });
function renderField(field, values = {}, props = {}) {
  const onChange = vi.fn();
  render(<FieldRenderer field={field} record={rec(values)} onChange={onChange} {...props} />);
  return onChange;
}

describe('FieldRenderer', () => {
  it('text: labelled input, counter, change sends {name: value}', () => {
    const onChange = renderField({ name: 'heading', label: 'Headline', type: 'text', max: 40, required: true }, { heading: 'Common Research &' });
    const input = screen.getByRole('textbox', { name: /Headline/ });
    expect(input).toHaveProperty('value', 'Common Research &');
    expect(screen.getByText('17 / 40')).toBeTruthy();
    fireEvent.change(input, { target: { value: 'New' } });
    expect(onChange).toHaveBeenCalledWith({ heading: 'New' }, undefined);
  });

  it('validates on blur, not while typing, and hides the error again on focus', () => {
    render(<FieldRenderer field={{ name: 'heading', label: 'Headline', type: 'text', required: true }} record={rec({ heading: '' })} onChange={() => {}} />);
    const input = screen.getByRole('textbox', { name: /Headline/ });
    expect(screen.queryByText('Enter headline.')).toBeNull();
    fireEvent.focusOut(input);
    expect(screen.getByText('Enter headline.')).toBeTruthy();
    expect(input.getAttribute('aria-invalid')).toBe('true');
    fireEvent.focusIn(input);
    expect(screen.queryByText('Enter headline.')).toBeNull();
  });

  it('shows a server error straight away', () => {
    renderField({ name: 'heading', label: 'Headline', type: 'text' }, { heading: 'x' }, { serverError: 'That name is taken.' });
    expect(screen.getByText('That name is taken.')).toBeTruthy();
  });

  it('boolean: a labelled switch that saves immediately', () => {
    const onChange = renderField({ name: 'is_published', label: 'Shown on site', type: 'boolean' }, { is_published: false });
    const sw = screen.getByRole('switch', { name: 'Shown on site' });
    fireEvent.click(sw);
    expect(onChange).toHaveBeenCalledWith({ is_published: true }, { immediate: true });
  });

  it('select: humanised choices and a placeholder for an empty value', () => {
    const onChange = renderField({ name: 'category', label: 'Category', type: 'select', choices: ['point-of-care', 'imaging'] }, { category: '' });
    const sel = screen.getByRole('combobox', { name: /Category/ });
    expect([...sel.options].map((o) => o.textContent)).toEqual(['Choose category', 'Point of care', 'Imaging']);
    fireEvent.change(sel, { target: { value: 'imaging' } });
    expect(onChange).toHaveBeenCalledWith({ category: 'imaging' }, { immediate: true });
  });

  it('select from a resource sends a number', () => {
    const onChange = renderField({ name: 'menu', label: 'Menu', type: 'select', choices_resource: 'navbar-menus' }, { menu: 1 }, { options: [{ value: 1, label: 'About' }, { value: 2, label: 'Research' }] });
    fireEvent.change(screen.getByRole('combobox', { name: /Menu/ }), { target: { value: '2' } });
    expect(onChange).toHaveBeenCalledWith({ menu: 2 }, { immediate: true });
  });

  it('number keeps digits only; url explains the accepted forms', () => {
    const onChange = renderField({ name: 'order', label: 'Order', type: 'number' }, { order: 1 });
    fireEvent.change(screen.getByRole('textbox', { name: /Order/ }), { target: { value: '1a2' } });
    expect(onChange).toHaveBeenCalledWith({ order: '12' }, undefined);
  });

  it('url hint and validation', () => {
    renderField({ name: 'link', label: 'Link', type: 'url' }, { link: 'innovations' });
    expect(screen.getByText(/A page on this site such as \/media/)).toBeTruthy();
    fireEvent.focusOut(screen.getByRole('textbox', { name: /Link/ }));
    expect(screen.getByText(/Use a page on this site like \/innovations/)).toBeTruthy();
  });

  it('textarea renders a labelled multi-line box', () => {
    renderField({ name: 'body', label: 'Statement', type: 'textarea' }, { body: 'Hello' });
    expect(screen.getByRole('textbox', { name: /Statement/ }).tagName).toBe('TEXTAREA');
  });
});

describe('validate.js', () => {
  it('counts characters of rich text without tags', () => {
    expect(validateField({ label: 'Body', type: 'richtext', max: 5 }, '<p>abcdef</p>')).toBe('Shorten to 5 characters (now 6).');
  });
  it('dates and numbers', () => {
    expect(validateField({ label: 'Date', type: 'date' }, '28/11/2026')).toMatch(/Enter a date/);
    expect(validateField({ label: 'N', type: 'number' }, 'x')).toMatch(/Enter a number/);
  });
  it('image size: reject below min width, warn below 1200', () => {
    expect(checkImageSize({ label: 'Photo', min_width: 1600 }, 1200).level).toBe('reject');
    expect(checkImageSize({ label: 'Photo' }, 900).level).toBe('warn');
    expect(checkImageSize({ label: 'Photo' }, 2400).level).toBe('ok');
  });
});
