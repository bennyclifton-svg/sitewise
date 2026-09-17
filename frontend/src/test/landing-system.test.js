import { readFileSync } from 'node:fs';
import { expect, it } from 'vitest';

const html = readFileSync('public/landing.html', 'utf8');
const css = readFileSync('public/landing-assets/landing-system.css', 'utf8');

it('places the project line field between the firm strip and the workspace', () => {
  document.body.innerHTML = html;
  const firms = document.getElementById('firm-concepts');
  const system = document.getElementById('project-system');
  const workspace = document.getElementById('project-workspace');
  expect(firms.compareDocumentPosition(system) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(system.compareDocumentPosition(workspace) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  const prompts = document.getElementById('how-it-works');
  expect(system.compareDocumentPosition(prompts) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(prompts.compareDocumentPosition(workspace) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

it('keeps only the directional line field', () => {
  document.body.innerHTML = html;
  const system = document.getElementById('project-system');
  expect(system.getAttribute('aria-hidden')).toBe('true');
  expect(system.children).toHaveLength(1);
  expect(system.firstElementChild.className).toBe('sw-system-linework');
  expect(system.querySelector('.sw-system-diagram-stage')).toBeNull();
  expect(system.querySelector('.sw-system-chip')).toBeNull();
  expect(system.querySelector('.sw-system-object')).toBeNull();
  expect(system.textContent.trim()).toBe('');
  expect(css).toContain('system-linework.svg');
  expect(css).not.toContain('sw-system-object');
});
