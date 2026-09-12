// Keep the insertion edge fixed: every new character displaces the prefix left.
export function typeHeadline(stage, lines, bounds) {
  const animations = [];
  const range = document.createRange();
  let delay = 0;
  for (const [index, line] of lines.entries()) {
    range.selectNodeContents(line);
    const target = range.getBoundingClientRect();
    const copy = document.createElement('span');
    copy.className = 'sw-typed-copy';
    copy.textContent = line.textContent;
    stage.append(copy);
    copy.style.left = `${target.left - bounds.left}px`;
    copy.style.top = `${target.top - bounds.top + (target.height - copy.getBoundingClientRect().height) / 2}px`;
    const width = copy.getBoundingClientRect().width;
    const lead = index === 0 ? 1000 : 350;
    const duration = line.textContent.length * 95;
    const frames = [{ transform: `translateX(${width}px)`, clipPath: 'inset(0 100% 0 0)' }];
    for (let length = 1; length <= line.textContent.length; length++) {
      range.setStart(line.firstChild, 0);
      range.setEnd(line.firstChild, length);
      const prefix = range.getBoundingClientRect().width;
      frames.push({
        transform: `translateX(${Math.max(0, width - prefix)}px)`,
        clipPath: `inset(0 ${Math.max(0, width - prefix)}px 0 0)`,
        easing: 'cubic-bezier(.2,.7,.3,1)',
      });
    }
    animations.push(copy.animate(frames, {
      id: 'sw-headline', delay: delay + lead, duration, fill: 'both',
    }));

    const cursor = document.createElement('span');
    cursor.className = 'sw-type-cursor';
    cursor.style.left = `${target.left - bounds.left}px`;
    cursor.style.top = `${target.top - bounds.top + target.height * .18}px`;
    stage.append(cursor);
    const travel = Math.min(width, bounds.width - (target.left - bounds.left) - cursor.getBoundingClientRect().width - 12);
    const total = lead + duration + 180;
    animations.push(cursor.animate([
      { transform: 'translateX(0)', offset: 0 },
      { transform: 'translateX(0)', offset: (lead - 300) / total },
      { transform: `translateX(${travel}px)`, offset: lead / total },
      { transform: `translateX(${travel}px)`, offset: 1 },
    ], { id: 'sw-headline', delay, duration: total, easing: 'ease-in-out', fill: 'both' }));
    // Low-contrast colour glitches vary by visit, without rapid on/off flashing.
    const flicker = Array.from({ length: Math.ceil(total / 200) }, (_, step) => ({
      opacity: step === 0 || step === Math.ceil(total / 200) - 1 ? 0 : (step % 3 === 0 ? .55 : 1),
      backgroundColor: Math.random() > .5 ? '#8ebeff' : '#f3f5fc',
      easing: 'steps(1, end)',
    }));
    animations.push(cursor.animate(flicker, {
      id: 'sw-headline', delay, duration: total, fill: 'both',
    }));
    delay += lead + duration + 180;
  }
  return { animations, duration: delay };
}
