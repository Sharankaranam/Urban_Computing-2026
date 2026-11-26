import { animate, stagger } from 'animejs'

const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

/** A short emphasis pulse, used when a rule starts firing. */
export function pulse(targets: Element[] | NodeListOf<Element>) {
  if (reduced() || !targets.length) return
  animate(targets as Element[], {
    scale: [{ to: 1.012, duration: 140 }, { to: 1, duration: 260 }],
    ease: 'outQuad',
  })
}

export { animate, stagger }
