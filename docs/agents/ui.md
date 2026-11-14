# UI standard: world-class, motion-first

Goal: the smoothest, most polished UI the user has ever seen, across web app, landing page and the Windows desktop app (same React UI inside Tauri). Smooth means 60/120 fps with zero jank, not "lots of effects".

## Stack (decided 2026-11-14, revisit only with the user)
- **Primitives:** shadcn/ui on Radix UI + Tailwind CSS. We own the component code; accessibility comes from Radix.
- **Motion:** Motion (formerly Framer Motion) for component, layout and shared-element transitions, gestures and springs. GSAP (+ ScrollTrigger) only for scroll-driven / timeline set pieces on the landing page. Lenis for smooth scroll on marketing pages only.
- **Showcase components:** Aceternity UI and Magic UI (copy-paste, built on Tailwind + Motion) for hero, landing and "wow" moments. Restyle them to our design system; never paste raw.
- **Not used:** Mantine, HeroUI, Flowbite. Each ships its own styling/theming system; mixing them with shadcn duplicates primitives, fragments motion and bloats bundles. Borrow ideas, not packages.
- Any new UI library needs user approval and a reason the current stack can't do it.

## Skills to use
- `ui-ux-pro-max`: once, to generate the design system (palette, type, spacing, radii, motion tokens) into `design-system/`. Then follow it.
- `frontend-design` + `award-tier-design-system` + `anti-slop-design`: every page/component. No generic AI-template look.
- `playwright-cli` / `webapp-testing`: screenshot every state, check console, test reduced-motion and keyboard paths.

## Motion rules (non-negotiable)
- Animate only `transform` and `opacity` (and `filter` sparingly). Never animate layout properties (width/height/top/left) directly; use Motion `layout` / FLIP.
- Springs over linear easing for interactive elements; one shared set of motion tokens (durations, springs, easings) from `design-system/`.
- Every interaction gives feedback in under 100 ms. Optimistic UI for user actions; skeletons, not spinners, for loading.
- Route/screen changes use shared-element or View Transitions; nothing pops in without an enter/exit.
- Respect `prefers-reduced-motion`: replace movement with fades, never remove feedback.
- Budget: no long tasks > 50 ms during animation; check with the Performance panel / Lighthouse; lazy-load heavy effects (GSAP, 3D) and keep them off the app's critical path.
- Motion must mean something (state change, hierarchy, causality). Decorative motion lives on the landing page, not in daily workflows.

## UI principles
- Accessibility: WCAG 2.2 AA, full keyboard support, visible focus, Radix semantics, 4.5:1 contrast, screen-reader labels, 44px touch targets.
- Consistency: everything from design tokens; no one-off colors, spacings or durations.
- Hierarchy and restraint: one primary action per view; generous whitespace; typographic scale from the design system.
- States: design empty, loading, error, offline, partial and success states for every screen.
- Dark and light themes from day one; responsive from 360 px to ultrawide; desktop app respects Windows theme.
- Trust UI for agent actions: every desktop/remote action shows what will happen, a risk level, approve/deny, and an undo or log entry.
