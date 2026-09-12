export const headlineMarks = {
  washDelay: 180,
};

export async function playHeadlineMarks(hero, { reducedMotion } = {}) {
  if (!hero) return;
  if (!reducedMotion && headlineMarks.washDelay) {
    await new Promise(resolve => setTimeout(resolve, headlineMarks.washDelay));
  }
  hero.classList.add('is-headline-washed');
}
