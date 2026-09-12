export function mountPromptExplorer(root) {
  const choices = [...root.querySelectorAll('.sw-prompt-choice')];
  const sizePreview = () => {
    const preview = root.querySelector('.sw-prompt-choice[open] .sw-prompt-preview');
    root.style.minHeight = window.matchMedia('(min-width: 900px)').matches && preview ? `${preview.getBoundingClientRect().height}px` : '';
  };
  const observer = new ResizeObserver(sizePreview);
  root.querySelectorAll('.sw-prompt-preview').forEach(preview => observer.observe(preview));
  const onToggle = event => {
    if (!event.target.open || !choices.includes(event.target)) return;
    choices.forEach(choice => { if (choice !== event.target) choice.open = false; });
    sizePreview();
    const preview = event.target.querySelector('.sw-prompt-preview');
    if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches && preview.animate) {
      preview.animate([{ opacity: .65, transform: 'translateY(4px)' }, { opacity: 1, transform: 'translateY(0)' }], { duration: 180, easing: 'cubic-bezier(.16,1,.3,1)' });
    }
  };
  root.addEventListener('toggle', onToggle, true);
  const onClick = event => {
    const mode = event.target.closest('[data-example-mode]');
    if (!mode) return;
    mode.closest('.sw-example-depth').querySelectorAll('button').forEach(button => {
      button.setAttribute('aria-pressed', String(button === mode));
    });
  };
  root.addEventListener('click', onClick);
  sizePreview();
  return () => { root.removeEventListener('toggle', onToggle, true); root.removeEventListener('click', onClick); observer.disconnect(); };
}

const explorer = document.querySelector('.sw-prompt-explorer');
if (explorer) mountPromptExplorer(explorer);
