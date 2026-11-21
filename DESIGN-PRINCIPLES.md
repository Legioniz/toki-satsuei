# TOKI SATSUEI — Experience Design Principles

This document records the practical rules behind the public website. The objective is to make the photography, information, and booking journey easier to understand—not to add decoration for its own sake.

## Brand constraints

- Keep the official TOKI SATSUEI brushstroke logo and original marks intact.
- Retain the charcoal / black, warm ivory, and restrained crimson palette.
- Preserve the honest positioning of the current gallery as practice and detail studies.
- Keep the small-team, Quezon City identity visible without implying an unverified studio size or client history.
- Photography remains the primary content. Decoration must not compete with the images.

## Principles translated into interface decisions

| Principle or theory | Rule applied | Website decision |
| --- | --- | --- |
| Visual hierarchy | Give each view one dominant message and one primary action. | The hero directs visitors to sessions and live availability. |
| Hick–Hyman law | Decision time generally grows with the number and complexity of choices. | Reduce homepage navigation to essential destinations; keep secondary information in the page and footer. |
| Gestalt proximity and similarity | Related information should look related; different tasks should be visibly separated. | Divide the inquiry into three numbered groups: session, date and place, contact and notes. |
| Fitts’s law | Important controls should be easy to acquire, especially on touch screens. | Main buttons, navigation links, and calendar controls use larger hit areas; key controls target about 44 CSS pixels. |
| Nielsen: visibility of system status | People should not have to guess whether an action worked. | Preserve live availability, submission status, and booking reference after acceptance. |
| Nielsen: error prevention | Prevent predictable mistakes early and validate again at the system boundary. | Browser and server both reject same-day requests for a time that has already passed. |
| Nielsen: match between system and real world | Use familiar terms and time conventions. | The form explicitly states Philippine Time and asks for exact 24-hour time. |
| Nielsen: recognition rather than recall | Show context where people make a choice. | Session cards show durations, prices, and inclusions; selecting one prefills the form. |
| Progressive disclosure | Present details in useful groups without hiding important conditions. | The request form groups fields by task and keeps the inquiry-not-reservation notice visible. |
| Motion sensitivity | Motion should aid orientation, never be required to understand the site. | The experience layer respects the operating-system reduced-motion setting. |

## Accessibility reference

WCAG 2.2 is the reference for contrast, reflow, keyboard access, and target sizes:

- Normal text contrast target: at least 4.5:1; large text: at least 3:1.
- Reflow target: no loss of information or functionality at 320 CSS pixels.
- Keyboard focus should be visible and controls should expose clear names and states.
- WCAG 2.2 AA defines a 24 by 24 CSS-pixel minimum target size, subject to exceptions. Major touch controls in this design aim for approximately 44 CSS pixels where layout allows.
- Type floor: no text renders below 11 CSS pixels. Decorative micro-labels use 11px; interactive and status text (navigation, buttons, filters, form legends, calendar status) uses 12px or larger.
- Reduced motion is respected; information and core actions remain available without animation.

Reference: [W3C Web Content Accessibility Guidelines (WCAG) 2.2](https://www.w3.org/TR/wcag/).

These are implementation targets, not a claim of formal WCAG conformance or independent certification.

## Booking integrity rules

1. A submitted form is an inquiry, not a reservation.
2. The public calendar displays confirmed time windows only and must not expose names, contact details, locations, or private notes.
3. Displayed booking times use Philippine time.
4. Same-day requests must be for a future minute. Browser validation improves the experience; server validation is authoritative.
5. The site must never claim a booking is confirmed until the team confirms it in writing.
6. Client photographs are not published without permission from the people featured.

## Quality gates

- Test layout from 320 CSS pixels through desktop widths.
- Check navigation and session selection with keyboard and pointer input.
- Check booking date/time minimums and error feedback.
- Run asset, security, calendar, booking, archive, policy, motion, and browser regression suites.
- Treat automated checks as regression evidence, not formal accessibility certification.

## Content clarity

- Do not present empty public collection shelves as if they contain browsable albums.
- Keep archive folders upload-ready in the repository, but expose only categories with published albums.
- Prefer direct official social links over an embedded social feed when there are too few current posts to make the feed useful.
- Keep privacy information accurate and visitor-readable; detailed backend implementation belongs in developer documentation, not customer-facing policy copy.

## Design system (design-system.css)

One stylesheet, loaded last, owns the visual language. Change a token and the whole site follows.

- **Tokens:** colour roles (paper 60 / ink 30 / accent 10), a fluid 1.25 type scale (`--step--1` to `--step-4`), an 8pt spacing scale (`--s-1` to `--s-8`), motion durations and easings (`--dur-*`, `--ease-*`) and sizing (`--tap`, `--header-h`).
- **UX rules applied:** Fitts (48px targets, booking button in the thumb zone on phones), Hick (one primary action per view; the floating button hides over the hero and the form), Gestalt proximity (consistent section rhythm), Doherty (feedback under 400ms), Miller (session cards 4 > 2 > 1 columns, never an orphan).
- **Adaptive:** fluid type and gutters; `orientation` and `max-height` rules for phones in landscape; safe-area insets for notches; `dvh/svh` units; `hover:none` and `pointer:coarse` handling; `prefers-reduced-motion` and `prefers-contrast`.
- **Motion:** cross-document view transitions (header stays fixed), staggered hero entrance, press and hover feedback, all disabled for reduced motion.
- **New components should use tokens, not raw values.**

## Touch targets and semantics

- Primary controls are at least 48px tall; standalone links and the skip link at least 44px; checkboxes 24px (WCAG 2.2 SC 2.5.8 requires 24px).
- The availability calendar is a labelled `group` of date buttons. Do not use `role="grid"` unless rows, column headers and arrow-key navigation are implemented.
- Run the accessibility scan after design changes: every public page should report zero axe violations.
