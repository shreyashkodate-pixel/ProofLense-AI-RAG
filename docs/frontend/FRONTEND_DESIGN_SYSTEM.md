# ProofLens AI — Frontend Design System

**Document status:** Draft v1.0 — pending product and accessibility review  
**Related canonical document:** `FRONTEND_DESIGN_TOKENS.md`

## 1. Product design intent

ProofLens AI is an evidence-first document Q&A and RAG experience. Its interface should help users distinguish an answer from the source evidence that supports it, navigate back to the source, and recognize when evidence is unavailable or an answer is uncertain.

The interface should feel calm, precise, credible, and efficient—not promotional or theatrically “AI-powered.”

### Design principles

- Evidence is a first-class part of the interface, not a decorative footnote.
- Keep the source document, cited passage, and generated answer visually distinguishable.
- Prefer clear labels and stable layouts over clever but ambiguous interactions.
- Preserve context when moving between a question, answer, citation, and source document.
- Use consistent loading, empty, failure, and retry states.
- Never visually imply a feature or guarantee that the backend does not provide.

## 2. Visual language

Follow `FRONTEND_DESIGN_TOKENS.md` for all canonical values.

- Light ivory canvas and white surfaces.
- Charcoal text and subtle borders.
- Restrained forest-green accent for primary actions and selected states.
- Muted semantic colors for success, warning, error, and informational states.
- Inter or a validated system-sans fallback.
- Modest radii and restrained shadows.
- No gradients, neon, glassmorphism, glowing AI orbs, or decorative animations.

The original reference images should be treated as visual inspiration, not as authorization to invent workflows or features.

## 3. Layout principles

The precise screen map must be derived from the approved PRD and verified backend capabilities.

- Use a consistent page shell and navigation hierarchy.
- Keep primary task content visually dominant.
- On desktop, use multiple panes only when they materially improve a workflow (for example, answer beside source evidence).
- On mobile, stack panes or provide explicit navigation between them; do not compress a desktop layout until it is unreadable.
- Keep primary actions in predictable locations.
- Make document identity and the currently selected workspace clear wherever relevant.
- Avoid introducing a separate screen for every small operation when an in-context panel or state is clearer.

## 4. Core component catalog

These are component specifications, not confirmation that every component or screen is required. Include a component in implementation only when supported by approved requirements.

### 4.1 Application shell and navigation

- Clear product identity and workspace context.
- Navigation labels must be explicit and consistent with approved feature names.
- Active navigation state uses accent color and a non-color cue such as weight or indicator.
- Mobile navigation must remain keyboard accessible and avoid obscuring the active workflow.

### 4.2 Buttons

Variants:
- **Primary:** one dominant action per local context; accent background with accessible text.
- **Secondary:** neutral surface, visible border.
- **Ghost:** low emphasis for tertiary actions.
- **Destructive:** semantic danger treatment and explicit action label.

States: default, hover, focus-visible, pressed, disabled, and loading. A loading button should prevent accidental duplicate submission where appropriate and expose status accessibly. Do not use icon-only controls without accessible names.

### 4.3 Inputs and search/query composer

- Visible label or an accessible equivalent; placeholder text is not a label.
- Distinct focus ring and error state.
- Inline validation explains how to recover.
- Preserve user-entered text after recoverable failures where safe.
- Query submission should not make unsupported promises about response time or answer certainty.

### 4.4 Cards, panels, and tables/lists

- Use surface and border tokens consistently.
- Maintain predictable internal padding and heading placement.
- Use rows, cards, or tables according to content density and viewport; do not force wide tables onto narrow screens.
- Make clickable rows discoverable without making an entire row ambiguously interactive.
- Distinguish selected, hovered, and focused states.

### 4.5 Status indicators

Status indicators must pair color with text and, where useful, an icon. Use only statuses verified in the backend and requirements. If the implementation confirms document states such as `pending`, `processing`, `ready`, and `failed`, display them with clear human-readable labels and accessible descriptions. Do not assume other states exist.

### 4.6 Citation and evidence components

A citation should communicate the source document and page or other location only when that information is returned by the backend.

- Make citations keyboard-operable links or buttons.
- Show clear hover and focus states.
- Distinguish cited evidence from surrounding explanation.
- Clicking a citation should navigate to the supported source location and preserve enough answer context to return.
- If a citation target cannot be loaded, show an explicit unavailable/error state rather than silently doing nothing.
- Never fabricate page numbers, snippets, chunk identifiers, or source references.

### 4.7 PDF and evidence viewer

The exact implementation depends on verified API contracts and PDF-library compatibility.

- Provide document identity and current page when supported.
- Treat physical PDF page numbers as one-indexed only if confirmed by backend contracts.
- If the backend provides text snippets but not bounding-box coordinates, use page navigation and carefully designed text search/match highlighting; do not draw invented geometric highlights.
- Distinguish an exact match, an approximate text match, multiple matches, and no match.
- Preserve the citation's source text and metadata as returned by the backend.
- Ensure the PDF delivery strategy can provide required authentication headers; do not assume a basic iframe can attach a custom workspace-key header.

### 4.8 Loading, empty, and error states

Every data-driven workflow should define:
- Initial loading state.
- Empty state with a clear next step, if an action is available.
- Recoverable error with a retry path.
- Permission/authentication error without exposing credentials.
- Not-found or unavailable state.
- Processing state where applicable.
- Partial or missing evidence state where applicable.

Avoid fake progress percentages unless real progress data is available. Prefer a stable skeleton or explicit activity indicator. Keep error copy concise and actionable; never display raw stack traces or secret-bearing server responses.

### 4.9 Toasts and notifications

- Use brief messages for transient outcomes.
- Do not rely on a toast as the only record of a critical error.
- Keep notifications non-blocking unless the user must resolve a decision.
- Ensure assistive technologies can discover important messages without overly chatty announcements.

### 4.10 Dialogs and popovers

- Use dialogs for focused decisions that require interruption; do not overuse them.
- Provide accessible labels and predictable keyboard behavior.
- Keep focus inside a modal while open and restore focus to the invoking control when closed.
- Ensure popovers are not clipped by scroll containers and can be dismissed accessibly.

## 5. Answer and evidence hierarchy

Where the approved product workflows include grounded Q&A, use a consistent hierarchy:

1. The user's question.
2. The generated answer.
3. Citations associated with claims, as provided by the backend.
4. Inspectable source evidence.
5. Any explicit uncertainty, abstention, or evidence-unavailable state supported by the backend.

Do not make unsupported claims that every sentence has a citation unless the actual response schema and product requirements guarantee that relationship. Preserve backend distinctions between answer text, citations, and evidence.

## 6. Interaction and motion

- Prefer immediate, predictable feedback.
- Use CSS transitions for simple state changes.
- Add GSAP only if a real interaction needs coordinated sequencing and the dependency is justified.
- Do not add Lenis by default; native scrolling is preferred unless requirements demonstrate a problem.
- Respect `prefers-reduced-motion`.
- Motion must not delay access to answers or source evidence.
- Avoid continuous decorative animation, parallax, and animated effects that distract from reading.

## 7. Accessibility requirements

Target WCAG 2.2 AA, subject to verification.

- Full keyboard operation for navigation, dialogs, citations, menus, and viewer controls.
- Visible focus indicator on all interactive elements.
- Semantic HTML and appropriate accessible names.
- Correct heading hierarchy and form labels.
- Status conveyed with text/icon in addition to color.
- Text resizing and 200% zoom without loss of essential content.
- Reflow at narrow viewport widths.
- Contrast testing for text, controls, borders, selected states, and evidence highlights.
- Reduced-motion support.
- Reasonable touch target sizing, with 44–48px preferred for primary touch controls where layout permits.

## 8. Responsive behavior

Use the breakpoints in `FRONTEND_DESIGN_TOKENS.md` as proposals until validated against the actual screen map and target devices.

- Mobile: prioritize the current task; stack complex panes; keep navigation and key actions reachable.
- Tablet: allow a two-pane view only when each pane retains usable width.
- Desktop: use space for source/evidence context, not for decorative whitespace alone.
- Wide desktop: constrain reading width and avoid long line lengths.

Responsive rules must be verified in implementation; a breakpoint table alone is not proof of responsive behavior.

## 9. Content and microcopy

- Use direct, plain English.
- Prefer sentence case.
- Explain what happened and what the user can do next.
- Use “evidence,” “citation,” “source document,” and “page” consistently with the product terminology.
- Avoid anthropomorphic AI copy, exaggerated confidence, and unsupported certainty.
- Do not show internal identifiers unless they are useful for troubleshooting or explicitly required.

## 10. Design-system acceptance checklist

Before implementation is considered aligned:

- [ ] Components use canonical design tokens instead of scattered raw values.
- [ ] Contrast has been measured and failing combinations corrected.
- [ ] Keyboard focus is visible and tested.
- [ ] All component states are defined.
- [ ] Status is not conveyed by color alone.
- [ ] Evidence and answer text are visually distinct.
- [ ] Citation navigation uses only verified backend metadata.
- [ ] PDF viewer behavior matches actual backend capabilities.
- [ ] Responsive behavior is defined for every approved screen.
- [ ] Reduced-motion behavior is tested.
- [ ] No prohibited decorative effects have been introduced.
- [ ] The UI contains no unapproved features or invented backend behavior.

## 11. Change control

`FRONTEND_DESIGN_TOKENS.md` is canonical for token names and values. This document defines usage and behavior. If a conflict occurs, update the canonical document after approval and then align implementation. Do not silently override tokens locally.

## 12. Open decisions

- Confirm exact visual reference colors if the original image assets or URLs are available for direct inspection.
- Validate contrast and adjust proposed colors as required.
- Confirm component and icon libraries against the actual repository.
- Finalize screen-specific layouts after `FRONTEND_REQUIREMENTS.md` is reconciled with the authoritative PRD and backend contracts.
