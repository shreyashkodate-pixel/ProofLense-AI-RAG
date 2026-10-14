# ProofLens AI — Frontend Design Tokens

**Document status:** Draft v1.0 — pending review and accessibility validation  
**Scope:** Canonical visual tokens for the ProofLens AI frontend  
**Implementation target:** Next.js frontend; CSS custom properties are the framework-neutral source of truth

> Important: Values in this document are proposed design decisions based on the visual direction established for ProofLens AI. They are not claimed to be pixel-sampled from the original reference images. Validate contrast and usability in the implemented interface before declaring this specification final.

## 1. Design principles

1. **Evidence first:** answers, citations, source passages, document identity, and page references must be visually distinguishable.
2. **Calm enterprise UI:** light ivory canvas, white surfaces, charcoal text, restrained forest-green accents.
3. **Clarity over decoration:** avoid gradients, neon, glassmorphism, glowing AI ornaments, and marketing-first patterns.
4. **Consistent interaction:** controls use predictable hover, focus, active, disabled, loading, success, and error states.
5. **Accessible by default:** keyboard operation, visible focus, adequate contrast, reduced-motion support, and minimum practical target sizes.
6. **Semantic use:** components consume semantic tokens (for example, `--color-text-primary`) rather than scattering raw hex values.

## 2. Color tokens

### 2.1 Base palette

| Token | Value | Intended use |
|---|---|---|
| `--color-canvas` | `#F7F7F4` | App/page background |
| `--color-surface` | `#FFFFFF` | Cards, dialogs, panels, menus |
| `--color-surface-alt` | `#F4F6F2` | Secondary panel or grouped region |
| `--color-surface-muted` | `#EEF3E9` | Subtle green-tinted emphasis |
| `--color-text-primary` | `#202720` | Main headings and body text |
| `--color-text-secondary` | `#58645B` | Supporting text and descriptions |
| `--color-text-tertiary` | `#737D75` | Metadata; verify contrast for each background |
| `--color-text-inverse` | `#FFFFFF` | Text on sufficiently dark filled controls |
| `--color-border` | `#E7E9E2` | Default dividers and borders |
| `--color-border-strong` | `#CDD4CA` | Emphasized borders |
| `--color-accent` | `#315A1B` | Primary actions, selected navigation, key links |
| `--color-accent-hover` | `#274916` | Hover state for accent actions |
| `--color-accent-pressed` | `#1F3A11` | Pressed state for accent actions |
| `--color-accent-soft` | `#EEF3E9` | Selected backgrounds and subtle emphasis |
| `--color-focus` | `#315A1B` | Focus ring; pair with offset and adequate contrast |

### 2.2 Semantic status colors

Status colors must never be the only means of communicating state. Pair them with a label, icon, or text.

| Token | Value | Intended use |
|---|---|---|
| `--color-success` | `#237A3B` | Completed or successful operation |
| `--color-success-soft` | `#EAF5EC` | Success background |
| `--color-warning` | `#975A00` | Warning or needs attention |
| `--color-warning-soft` | `#FFF4D8` | Warning background |
| `--color-danger` | `#B42318` | Error, destructive action, failed operation |
| `--color-danger-soft` | `#FDECEA` | Error background |
| `--color-info` | `#2457A7` | Informational state |
| `--color-info-soft` | `#EAF1FC` | Informational background |

These semantic values are proposals and must be contrast-tested with their intended text and background combinations.

### 2.3 Evidence and citation colors

| Token | Value | Intended use |
|---|---|---|
| `--color-evidence-highlight` | `#E7EFD9` | Source text that matches cited evidence |
| `--color-evidence-selected` | `#DDEBCB` | Currently selected evidence passage |
| `--color-evidence-outline` | `#8DA878` | Outline or marker for selected evidence |
| `--color-citation-tag` | `#315A1B` | Citation chip background where contrast is verified |
| `--color-citation-tag-text` | `#FFFFFF` | Text on citation chip |
| `--color-evidence-unavailable` | `#F1F2EF` | Missing or unavailable evidence region |

Evidence highlighting must not imply that the backend supplied exact PDF bounding boxes if it only provides page numbers and text snippets. Text-match highlighting should be described honestly and must handle ambiguous or absent matches.

## 3. Typography

**Preferred family:** Inter, with system sans-serif fallbacks. Confirm font delivery and licensing/hosting choices during frontend foundation work.

```css
font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
  "Segoe UI", sans-serif;
```

| Token | Size / line height | Weight | Use |
|---|---:|---:|---|
| `--font-size-xs` | 12px / 16px | 400–500 | Dense metadata, helper text |
| `--font-size-sm` | 14px / 20px | 400–500 | Secondary text, controls |
| `--font-size-md` | 16px / 24px | 400 | Default body copy |
| `--font-size-lg` | 18px / 28px | 400–500 | Lead copy or emphasized answer text |
| `--font-size-xl` | 20px / 28px | 600 | Card or subsection heading |
| `--font-size-2xl` | 24px / 32px | 600 | Page section heading |
| `--font-size-3xl` | 30px / 38px | 650–700 | Page title, use sparingly |
| `--font-size-4xl` | 36px / 44px | 700 | Large workspace heading, if needed |

Use sentence case for headings and buttons. Prefer readable line lengths for document passages and answers. Do not reduce evidence text below 14px in normal viewing contexts.

## 4. Spacing scale

Use a 4px base scale. Prefer the named tokens instead of arbitrary spacing values.

| Token | Value |
|---|---:|
| `--space-0` | 0px |
| `--space-1` | 4px |
| `--space-2` | 8px |
| `--space-3` | 12px |
| `--space-4` | 16px |
| `--space-5` | 20px |
| `--space-6` | 24px |
| `--space-8` | 32px |
| `--space-10` | 40px |
| `--space-12` | 48px |
| `--space-16` | 64px |
| `--space-20` | 80px |

Guidance:
- 8–12px for compact control internals.
- 16–24px for card and panel padding.
- 24–32px between major content groups.
- Preserve sufficient breathing room around citations and evidence snippets.
- Dense data views may use compact spacing only when readability remains intact.

## 5. Borders and radii

### Border widths

| Token | Value | Use |
|---|---:|---|
| `--border-width-thin` | 1px | Default card, input, and divider |
| `--border-width-medium` | 2px | Focus, selected, or emphasized outline |
| `--border-width-thick` | 3px | Rare high-emphasis indicator |

### Radius

| Token | Value | Use |
|---|---:|---|
| `--radius-xs` | 4px | Small labels and compact controls |
| `--radius-sm` | 6px | Inputs, small buttons |
| `--radius-md` | 8px | Standard buttons, cards, menus |
| `--radius-lg` | 12px | Larger panels and dialogs |
| `--radius-xl` | 16px | Major containers where justified |
| `--radius-pill` | 999px | Chips and fully rounded status labels only |

Use restrained rounding. Avoid making every panel pill-shaped or excessively rounded.

## 6. Shadows and elevation

Use shadows sparingly; rely primarily on whitespace and borders.

| Token | Value | Use |
|---|---|---|
| `--shadow-sm` | `0 1px 2px rgb(32 39 32 / 5%)` | Hoverable card or small menu |
| `--shadow-md` | `0 4px 12px rgb(32 39 32 / 8%)` | Popover or floating panel |
| `--shadow-lg` | `0 8px 24px rgb(32 39 32 / 12%)` | Modal or high elevation overlay |

Do not use colored glow shadows. Elevation must not be the only cue that separates interactive elements.

## 7. Layout and responsive breakpoints

Proposed breakpoints (confirm against the actual screen map and test devices):

| Token | Value | Guidance |
|---|---:|---|
| `--breakpoint-sm` | 640px | Large phones / small tablet transition |
| `--breakpoint-md` | 768px | Tablet layouts |
| `--breakpoint-lg` | 1024px | Compact desktop layouts |
| `--breakpoint-xl` | 1280px | Standard desktop workspace |
| `--breakpoint-2xl` | 1536px | Wide desktop |

Layout guidance:
- Use a fluid content width with a proposed maximum of 1280px for standard content pages.
- Use a 12-column grid on wide screens where it simplifies alignment.
- Proposed desktop gutter: 24px; compact gutter: 16px; mobile page padding: 16px.
- Do not force multi-panel desktop layouts onto small screens. Stack panels or use explicit navigation between them.
- PDF/evidence and answer panes may need different responsive behavior; define it per workflow in `FRONTEND_REQUIREMENTS.md`.

## 8. Component sizing and interaction

| Token | Value | Use |
|---|---:|---|
| `--control-height-sm` | 32px | Dense secondary controls |
| `--control-height-md` | 40px | Standard input/button |
| `--control-height-lg` | 48px | Primary or touch-oriented control |
| `--icon-size-sm` | 16px | Inline icon |
| `--icon-size-md` | 20px | Default control icon |
| `--icon-size-lg` | 24px | Prominent action icon |
| `--focus-ring-width` | 2px | Keyboard focus indicator |
| `--focus-ring-offset` | 2px | Space between control and ring |

Use an icon set consistently (Lucide is a proposed choice, subject to repository dependencies). Icons must have accessible names when they convey meaning. Icon-only buttons require an accessible label.

Required component states:
- Default
- Hover (where hover exists)
- Focus-visible
- Active/pressed
- Disabled
- Loading
- Success/error where applicable

Never communicate status only by color. Destructive actions require clear wording and appropriate confirmation where the operation warrants it.

## 9. Motion

Motion is functional and restrained. CSS transitions are the default; add animation libraries only when a verified interaction genuinely benefits from them.

| Token | Value |
|---|---|
| `--motion-duration-fast` | 150ms |
| `--motion-duration-base` | 200ms |
| `--motion-duration-slow` | 300ms |
| `--motion-ease-standard` | `cubic-bezier(0.2, 0, 0, 1)` |

Use motion for small state changes, panel transitions, and clear feedback. Avoid continuous decorative animation and animation that delays access to content.

Respect `prefers-reduced-motion: reduce`; remove nonessential movement and reduce transition duration. Do not add GSAP or Lenis by default.

## 10. Layering / z-index

| Token | Value | Use |
|---|---:|---|
| `--z-base` | 0 | Normal document flow |
| `--z-sticky` | 10 | Sticky header or local sticky controls |
| `--z-dropdown` | 20 | Menus and popovers |
| `--z-overlay` | 30 | Modal backdrop |
| `--z-modal` | 40 | Modal/dialog |
| `--z-toast` | 50 | Toast notifications |
| `--z-tooltip` | 60 | Tooltips, if not clipped by overlays |

Centralize layer values. Avoid arbitrary per-component z-index escalation.

## 11. CSS custom property reference

The following is the proposed initial token layer. Keep component-specific styling mapped to these semantic values.

```css
:root {
  color-scheme: light;

  --color-canvas: #F7F7F4;
  --color-surface: #FFFFFF;
  --color-surface-alt: #F4F6F2;
  --color-surface-muted: #EEF3E9;

  --color-text-primary: #202720;
  --color-text-secondary: #58645B;
  --color-text-tertiary: #737D75;
  --color-text-inverse: #FFFFFF;

  --color-border: #E7E9E2;
  --color-border-strong: #CDD4CA;
  --color-accent: #315A1B;
  --color-accent-hover: #274916;
  --color-accent-pressed: #1F3A11;
  --color-accent-soft: #EEF3E9;
  --color-focus: #315A1B;

  --color-success: #237A3B;
  --color-success-soft: #EAF5EC;
  --color-warning: #975A00;
  --color-warning-soft: #FFF4D8;
  --color-danger: #B42318;
  --color-danger-soft: #FDECEA;
  --color-info: #2457A7;
  --color-info-soft: #EAF1FC;

  --color-evidence-highlight: #E7EFD9;
  --color-evidence-selected: #DDEBCB;
  --color-evidence-outline: #8DA878;
  --color-citation-tag: #315A1B;
  --color-citation-tag-text: #FFFFFF;
  --color-evidence-unavailable: #F1F2EF;

  --font-sans: Inter, ui-sans-serif, system-ui, -apple-system,
    BlinkMacSystemFont, "Segoe UI", sans-serif;

  --space-0: 0px;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;
  --space-20: 80px;

  --border-width-thin: 1px;
  --border-width-medium: 2px;
  --border-width-thick: 3px;

  --radius-xs: 4px;
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-pill: 999px;

  --shadow-sm: 0 1px 2px rgb(32 39 32 / 5%);
  --shadow-md: 0 4px 12px rgb(32 39 32 / 8%);
  --shadow-lg: 0 8px 24px rgb(32 39 32 / 12%);

  --control-height-sm: 32px;
  --control-height-md: 40px;
  --control-height-lg: 48px;
  --icon-size-sm: 16px;
  --icon-size-md: 20px;
  --icon-size-lg: 24px;
  --focus-ring-width: 2px;
  --focus-ring-offset: 2px;

  --motion-duration-fast: 150ms;
  --motion-duration-base: 200ms;
  --motion-duration-slow: 300ms;
  --motion-ease-standard: cubic-bezier(0.2, 0, 0, 1);

  --z-base: 0;
  --z-sticky: 10;
  --z-dropdown: 20;
  --z-overlay: 30;
  --z-modal: 40;
  --z-toast: 50;
  --z-tooltip: 60;
}

@media (prefers-reduced-motion: reduce) {
  :root {
    --motion-duration-fast: 1ms;
    --motion-duration-base: 1ms;
    --motion-duration-slow: 1ms;
  }
}
```

## 12. Accessibility and validation gates

Before these tokens are marked final:

- Measure WCAG 2.2 AA contrast for normal text, large text, controls, borders where needed, and status combinations.
- Check focus visibility on canvas, surface, accent, and status backgrounds.
- Confirm that evidence highlight remains legible with selected text and in PDF/text contexts.
- Test browser zoom to 200% and narrow viewport layouts.
- Verify keyboard access and visible focus for every interactive component.
- Check reduced-motion behavior.
- Confirm semantic status labels are present and not represented by color alone.

Do not declare compliance based on palette inspection alone. Record test results in the frontend verification documentation.

## 13. Change control

- This document is the canonical source for token names and values.
- `FRONTEND_DESIGN_SYSTEM.md` explains how components should use these tokens.
- Implementation code must not introduce one-off colors or spacing values without a documented reason.
- Any approved token change must be updated here first, then propagated to code and dependent documentation.
- Backend contracts and product requirements take precedence over any visual treatment.

## 14. Open decisions

1. Confirm exact colors against the original visual references if source images/URLs become available for direct inspection.
2. Run contrast checks and adjust any values that fail.
3. Confirm whether Inter and the proposed icon library fit the actual repository and deployment constraints.
4. Validate breakpoints and layout maximums against the approved screen map.
5. Finalize only after the frontend documentation review.
