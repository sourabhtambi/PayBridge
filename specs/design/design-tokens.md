# PayBridge Design Tokens

Style: clean, professional banking dashboard. Deep navy chrome, white surfaces, one blue action colour, restrained semantic colours. WCAG 2.1 AA. No external fonts (system font stack). The CSS form of these tokens is `specs/design/mockups/tokens.css`, inlined unchanged into every mockup.

## Colour tokens

| Token (CSS var `--color-*`) | Hex | Role |
|---|---|---|
| `bg` | `#F4F6FA` | Page background |
| `surface` | `#FFFFFF` | Cards, tables, inputs |
| `surface-sunken` | `#EAEFF6` | Table headers, code blocks, tag backgrounds |
| `text` | `#101C32` | Primary text |
| `text-secondary` | `#44506A` | Secondary text, table headers |
| `text-muted` | `#566178` | Hints, captions |
| `primary` | `#0B57B7` | Primary button, links, focus ring |
| `primary-hover` | `#09448F` | Primary hover |
| `on-primary` | `#FFFFFF` | Text on primary / danger solid |
| `link` | `#0B57B7` | Link text |
| `border-strong` | `#6B7689` | Input and control boundary (3:1) |
| `divider` | `#D3DAE6` | Decorative separators only |
| `focus-ring` | `#0B57B7` | Focus indicator on light |
| `focus-ring-on-dark` | `#FFD166` | Focus indicator on navy chrome |
| `nav-bg` | `#0B2545` | Header and nav background |
| `nav-text` | `#FFFFFF` | Nav text |
| `nav-text-muted` | `#BFD0E6` | Nav labels |
| `nav-active-bg` | `#1B4577` | Active nav item |
| `dev-bg` | `#1F2937` | Mockup control bar (not product) |
| `dev-text` | `#F9FAFB` | Mockup control bar text |
| `neutral-bg` | `#E6EBF3` | Badge CREATED |
| `neutral-text` | `#2E3A52` | Badge CREATED text |
| `info-bg` | `#E1EDFF` | Badge SUBMITTED / APPROVED |
| `info-text` | `#0A3F86` | Badge info text |
| `success-bg` | `#E3F5EA` | Badge COMPLETED / EXECUTED / matched |
| `success-text` | `#0B6A33` | Success text |
| `warn-bg` | `#FFF3D1` | Badge REQUESTED / unmatched / transient / STUCK |
| `warn-text` | `#6F4A00` | Warning text |
| `danger-bg` | `#FDECEC` | Badge FAILED / REJECTED, error banner |
| `danger-text` | `#A1161B` | Error text |
| `danger-border` | `#C0262B` | Error border, invalid input |
| `danger-solid` | `#B3201F` | Reject button |
| `disabled-bg` | `#E1E5EC` | Disabled button |
| `disabled-text` | `#566178` | Disabled label |
| `placeholder` | `#5F6B80` | Input placeholder |
| `skeleton` | `#DCE3EE` | Skeleton shimmer base (decorative) |
| `skeleton-hi` | `#EEF2F8` | Skeleton shimmer highlight (decorative) |

## Contrast proof

Computed by `python3` (WCAG 2.1 relative luminance, ratio = (L1+0.05)/(L2+0.05)). Text pairs require 4.5:1; control boundaries and focus rings (non-text) require 3:1. Decorative values (`divider`, `skeleton*`) are excluded because they carry no information.

| Foreground | Background | Used for | Ratio | Required | Result |
|---|---|---|---|---|---|
| `text` #101C32 | `bg` #F4F6FA | Body text on page | 15.73:1 | 4.5:1 | PASS |
| `text` #101C32 | `surface` #FFFFFF | Body text on cards/tables | 17.02:1 | 4.5:1 | PASS |
| `text` #101C32 | `surface-sunken` #EAEFF6 | Body text on sunken panels | 14.73:1 | 4.5:1 | PASS |
| `text-secondary` #44506A | `bg` #F4F6FA | Secondary text on page | 7.46:1 | 4.5:1 | PASS |
| `text-secondary` #44506A | `surface` #FFFFFF | Secondary text on cards | 8.07:1 | 4.5:1 | PASS |
| `text-secondary` #44506A | `surface-sunken` #EAEFF6 | Secondary text on sunken | 6.99:1 | 4.5:1 | PASS |
| `text-muted` #566178 | `bg` #F4F6FA | Muted text (captions, hints) on page | 5.75:1 | 4.5:1 | PASS |
| `text-muted` #566178 | `surface` #FFFFFF | Muted text on cards | 6.22:1 | 4.5:1 | PASS |
| `text-muted` #566178 | `surface-sunken` #EAEFF6 | Muted text on sunken | 5.38:1 | 4.5:1 | PASS |
| `placeholder` #5F6B80 | `surface` #FFFFFF | Input placeholder | 5.38:1 | 4.5:1 | PASS |
| `link` #0B57B7 | `surface` #FFFFFF | Link text on cards | 6.86:1 | 4.5:1 | PASS |
| `link` #0B57B7 | `bg` #F4F6FA | Link text on page | 6.34:1 | 4.5:1 | PASS |
| `link` #0B57B7 | `surface-sunken` #EAEFF6 | Link text on sunken | 5.94:1 | 4.5:1 | PASS |
| `on-primary` #FFFFFF | `primary` #0B57B7 | Primary button label | 6.86:1 | 4.5:1 | PASS |
| `on-primary` #FFFFFF | `primary-hover` #09448F | Primary button label (hover) | 9.40:1 | 4.5:1 | PASS |
| `on-primary` #FFFFFF | `danger-solid` #B3201F | Danger button label | 6.68:1 | 4.5:1 | PASS |
| `nav-text` #FFFFFF | `nav-bg` #0B2545 | Nav and header text | 15.39:1 | 4.5:1 | PASS |
| `nav-text-muted` #BFD0E6 | `nav-bg` #0B2545 | Nav secondary text/labels | 9.80:1 | 4.5:1 | PASS |
| `nav-text` #FFFFFF | `nav-active-bg` #1B4577 | Active nav item | 9.70:1 | 4.5:1 | PASS |
| `nav-text-muted` #BFD0E6 | `nav-active-bg` #1B4577 | Muted text on active nav | 6.18:1 | 4.5:1 | PASS |
| `dev-text` #F9FAFB | `dev-bg` #1F2937 | Dev bar text | 14.05:1 | 4.5:1 | PASS |
| `neutral-text` #2E3A52 | `neutral-bg` #E6EBF3 | Badge CREATED / neutral | 9.52:1 | 4.5:1 | PASS |
| `info-text` #0A3F86 | `info-bg` #E1EDFF | Badge SUBMITTED / info | 8.59:1 | 4.5:1 | PASS |
| `success-text` #0B6A33 | `success-bg` #E3F5EA | Badge COMPLETED / success | 5.93:1 | 4.5:1 | PASS |
| `warn-text` #6F4A00 | `warn-bg` #FFF3D1 | Badge warn (stuck, unmatched) | 7.15:1 | 4.5:1 | PASS |
| `danger-text` #A1161B | `danger-bg` #FDECEC | Badge FAILED / error banner | 6.95:1 | 4.5:1 | PASS |
| `danger-text` #A1161B | `surface` #FFFFFF | Field error text on cards | 7.94:1 | 4.5:1 | PASS |
| `danger-text` #A1161B | `bg` #F4F6FA | Field error text on page | 7.34:1 | 4.5:1 | PASS |
| `success-text` #0B6A33 | `surface` #FFFFFF | Success text on cards | 6.72:1 | 4.5:1 | PASS |
| `disabled-text` #566178 | `disabled-bg` #E1E5EC | Disabled button label (exempt, still met) | 4.92:1 | 4.5:1 | PASS |
| `border-strong` #6B7689 | `surface` #FFFFFF | Input / control boundary on card | 4.59:1 | 3:1 | PASS |
| `border-strong` #6B7689 | `bg` #F4F6FA | Input / control boundary on page | 4.24:1 | 3:1 | PASS |
| `danger-border` #C0262B | `danger-bg` #FDECEC | Error banner boundary | 5.17:1 | 3:1 | PASS |
| `danger-border` #C0262B | `surface` #FFFFFF | Invalid input boundary on card | 5.91:1 | 3:1 | PASS |
| `focus-ring` #0B57B7 | `surface` #FFFFFF | Focus ring on cards | 6.86:1 | 3:1 | PASS |
| `focus-ring` #0B57B7 | `bg` #F4F6FA | Focus ring on page | 6.34:1 | 3:1 | PASS |
| `focus-ring` #0B57B7 | `surface-sunken` #EAEFF6 | Focus ring on sunken | 5.94:1 | 3:1 | PASS |
| `focus-ring-on-dark` #FFD166 | `nav-bg` #0B2545 | Focus ring in nav | 10.67:1 | 3:1 | PASS |
| `focus-ring-on-dark` #FFD166 | `dev-bg` #1F2937 | Focus ring in dev bar | 10.18:1 | 3:1 | PASS |
| `primary` #0B57B7 | `surface` #FFFFFF | Primary button boundary on card | 6.86:1 | 3:1 | PASS |

Result: 40 of 40 pairs pass. Reproduce with `python3 specs/design/contrast_check.py`; the E9-S3 mockup also recomputes in the browser.

## Colour-independent status

Every status renders as a badge containing the enum text (for example `COMPLETED`, `amount_mismatch`) plus a decorative glyph (aria-hidden) and a 1px currentColor border. Colour is reinforcement only. See E9-S3 for the full set and a greyscale preview.

## Typography

- Sans: `"Segoe UI", "Helvetica Neue", "Noto Sans", "Liberation Sans", sans-serif`
- Mono (IDs, checksums, codes): `ui-monospace, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace`
- Amounts use `font-variant-numeric: tabular-nums`.

| Token | Size | Use |
|---|---|---|
| `--fs-xs` | 12px | badges, annotations, table headers |
| `--fs-sm` | 14px | table body, hints, labels |
| `--fs-md` | 16px | body |
| `--fs-lg` | 18px | card titles |
| `--fs-xl` | 22px | page title on mobile, tile values |
| `--fs-2xl` | 28px | page title desktop |
| `--fs-3xl` | 34px | reserved |

Line heights: `--lh-tight` 1.25 (headings), `--lh-body` 1.5.

## Spacing (4px grid)

`--s-1` 4, `--s-2` 8, `--s-3` 12, `--s-4` 16, `--s-5` 24, `--s-6` 32, `--s-7` 40, `--s-8` 56 (px).

## Radius

`--radius-sm` 4px (tags, focus), `--radius-md` 8px (controls), `--radius-lg` 12px (cards, dialog), `--radius-pill` 999px (badges).

## Elevation

| Token | Value | Use |
|---|---|---|
| `--elev-0` | none | flat |
| `--elev-1` | 0 1px 2px rgba(16,28,50,.08) | cards, tiles |
| `--elev-2` | 0 4px 12px rgba(16,28,50,.12) | menus (reserved) |
| `--elev-3` | 0 12px 32px rgba(16,28,50,.24) | dialog, skip link |

## Breakpoints and layout

- Tables stack into labelled rows at max-width 640px (no horizontal scroll at 375px). 4-column tile grids drop to 2 columns at 960px and 1 column at 640px.
- Content max width 1180px.

## Interaction rules

- Focus: `:focus-visible` 3px solid `--color-focus-ring`, offset 2px; yellow `--color-focus-ring-on-dark` inside the navy header, nav and controls bar.
- Targets: controls 40px tall (44px inputs and mobile buttons).
- Reduced motion: shimmer and spinner animations are disabled under `prefers-reduced-motion`.
- Errors: `role="alert"`, text plus warning glyph, `aria-invalid` on the field, border 2px `danger-border`.
