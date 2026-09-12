/* global document, window, requestAnimationFrame */
const headline = document.querySelector('.headline');
function replay() {
  headline.classList.remove('reveal');
  requestAnimationFrame(() => requestAnimationFrame(() => headline.classList.add('reveal')));
}
document.querySelectorAll('button[data-cut]').forEach(button => {
  button.addEventListener('click', () => {
    document.body.dataset.cut = button.dataset.cut;
    document.querySelectorAll('button[data-cut]').forEach(item => item.setAttribute('aria-pressed', String(item.dataset.cut === button.dataset.cut)));
    replay();
  });
});
document.querySelectorAll('button[data-tone]').forEach(button => {
  button.addEventListener('click', () => {
    document.body.dataset.tone = button.dataset.tone;
    document.querySelectorAll('button[data-tone]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
  });
});
document.querySelector('#replay').addEventListener('click', replay);
let pending = false;
window.addEventListener('scroll', () => {
  if (pending) return;
  pending = true;
  requestAnimationFrame(() => {
    const bounds = document.querySelector('.scroll-study').getBoundingClientRect();
    const progress = Math.max(0, Math.min(1, (72 - bounds.top) / (window.innerHeight * .45)));
    document.body.style.setProperty('--progress', progress);
    pending = false;
  });
}, {passive:true});
document.fonts.ready.then(replay);
