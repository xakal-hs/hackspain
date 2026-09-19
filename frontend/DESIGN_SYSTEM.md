# X-Ray design system

This application translates the supplied Clerk-style reference into a lender-facing financial-health workspace. It keeps the reference's mixed light/dark surfaces and restrained violet brand, while reserving green, amber, and red for financial meaning. The product itself—not decorative illustration—is the visual evidence.

## Principles

1. **A decision before a dashboard.** Every company view must answer lend, watch, or do not lend before exposing diagnostic detail.
2. **Trajectory beside level.** A score without its direction and horizon is incomplete.
3. **Coverage is not health.** Confidence and ERP coverage are neutral observability signals.
4. **Plain language first.** “Money left in the account” precedes “liquidity runway”; “time to get paid” precedes “DSO”.
5. **Violet means action.** `#6c47ff` is for primary actions, focus, and product identity—never health status.

## Core tokens

| Role | Token | Value |
|---|---|---|
| Page canvas | `--color-fog-white` | `#f7f7f8` |
| Card | `--color-pure-white` | `#ffffff` |
| Primary text | `--color-void-black` | `#131316` |
| Secondary text | `--color-graphite` | `#5e5f6e` |
| Hairline | `--color-hairline` | `#d9d9de` |
| Product surface | `--color-obsidian-card` | `#212126` |
| Elevated dark surface | `--color-dark-surface` | `#2f3037` |
| Primary action | `--color-electric-violet` | `#6c47ff` |
| Healthy | `--color-healthy` | `#168a62` |
| Watch | `--color-watch` | `#b55f00` |
| Risk | `--color-risk` | `#c43838` |

Geist is the UI and data face; Geist Mono is restricted to code-like system labels. Large cards use 16px radii, controls 6px, and pills are fully rounded. The content width caps at 1200px.

## Surfaces and hierarchy

- Use the fog canvas for the workspace and white for tables and controls.
- Use obsidian only for decision previews, scenario results, and other high-attention product evidence.
- Dark cards have an inset shimmer, not a visible border or drop shadow.
- Use the atmospheric violet/yellow halo once per view at most, behind the primary product preview.

## Accessibility

- Body text is at least 16px where prose is read; table metadata may be 12–13px.
- Interactive targets are at least 44px in either height or hit area.
- Every icon-only control has an accessible name and visible focus.
- Status always combines color with text and/or shape.
- Reduced-motion users receive no non-essential movement.
