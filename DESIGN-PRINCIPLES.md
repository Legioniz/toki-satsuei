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
