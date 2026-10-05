# Frontend (React, TypeScript, Vite)

Inherits `/CLAUDE.md`.

## Commands
- Test: `npm test` (Vitest with coverage) | Lint: `npm run lint` | Types: `npm run typecheck`
- E2E: `npm run e2e` (Playwright; needs backend on 8000 and the dev server on 3000)

## Layout (`src/`)
`types/`, `config/`, `service/`, `api/`, `ui/`. Nothing outside `ui/` imports from `ui/`.

## Rules
- **Money is integer paise in all state, props and API payloads.** Convert paise → rupees only when rendering, and rupees → paise only when reading form input. Use `service/money.ts`; never `toFixed` or float math on amounts.
- Display rupees with Indian digit grouping (for example `Rs 1,00,000.50`).
- TypeScript strict; no `any`. API response types live in `types/` and `api/`.
- Fetch and poll through the `ui/hooks` helpers (`useResource`, `usePolling`); components stay presentational.
- Accessibility (WCAG 2.1 AA): labelled fields, keyboard navigation, status shown as text and a glyph, never colour alone.
- Payment states: CREATED, SUBMITTED, COMPLETED, FAILED, REFUNDED. Add new states to `types/domain.ts`, `StateBadge`, and the dashboard together.
- Roles come from the `X-Role` / `X-Customer-Id` headers (demo only, not security).
- Tests live beside the source (`*.test.ts(x)`); Playwright specs are in `e2e/`.
