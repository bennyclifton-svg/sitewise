export const headlineReveal = {
  duration: 1100,
  easing: 'cubic-bezier(.16, 1, .3, 1)',
  shift: '0.55em',
  stagger: 160,
  mask: {
    duration: 1680,
    easing: 'cubic-bezier(.65, 0, .92, .35)',
    image: 'linear-gradient(to top, #000 38%, transparent 92%)',
    size: '100% 380%',
    from: '0% 0%',
    to: '0% 100%',
    feather: 0.54,
  },
};

function play(animate, element, frames, options) {
  return animate(element, frames, options);
}

export function revealHeadlineLines(lines, { animate, reducedMotion } = {}) {
  if (reducedMotion) return [];
  const run = animate ?? ((element, frames, options) => element.animate(frames, options));
  const mask = headlineReveal.mask;
  return [...lines].flatMap((line, index) => {
    const ink = line.querySelector('.sw-headline-ink') ?? line;
    const shared = { id: 'sw-headline', delay: index * headlineReveal.stagger, fill: 'both' };
    return [
      play(run, line, [
        {
          maskImage: mask.image,
          maskSize: mask.size,
          maskPosition: mask.from,
          maskRepeat: 'no-repeat',
          webkitMaskImage: mask.image,
          webkitMaskSize: mask.size,
          webkitMaskPosition: mask.from,
          webkitMaskRepeat: 'no-repeat',
        },
        {
          maskImage: mask.image,
          maskSize: mask.size,
          maskPosition: mask.to,
          maskRepeat: 'no-repeat',
          webkitMaskImage: mask.image,
          webkitMaskSize: mask.size,
          webkitMaskPosition: mask.to,
          webkitMaskRepeat: 'no-repeat',
        },
      ], { ...shared, duration: mask.duration, easing: mask.easing }),
      play(run, ink, [
        { transform: `translateY(${headlineReveal.shift})` },
        { transform: 'translateY(0)' },
      ], { ...shared, duration: headlineReveal.duration, easing: headlineReveal.easing }),
    ];
  });
}
