// Tour state and card model. Pure: no DOM, no map.

// Steps wrap at both ends; goto clamps.
export function createTour(steps) {
  const n = steps.length;
  const t = {
    index: 0,
    current: () => steps[t.index],
    next: () => { t.index = (t.index + 1) % n; return t.current(); },
    prev: () => { t.index = (t.index - 1 + n) % n; return t.current(); },
    goto: (i) => { t.index = Math.max(0, Math.min(n - 1, i | 0)); return t.current(); },
  };
  return t;
}

// The card shows the Commons photo when we have it, else a snapshot of our 3D view.
export function cardPhoto(step, photos) {
  const ph = step && step.photo && photos ? photos[step.photo] : null;
  if (!ph || !ph.src) return { kind: "snapshot" };
  return { kind: "photo", src: ph.src, credit: ph.credit, page: ph.page };
}
