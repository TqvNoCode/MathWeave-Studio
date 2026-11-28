# MathWeave Studio — UI/UX Design System

**Design System Version:** 1.1 (UI/UX Unification + Post-Review Polish)  
**Application Version:** MathWeave Studio `v0.3.1` (`pyproject.toml` & `math_app.__version__`)
**Architecture Layer:** `src/math_app/presentation/`  
**Design Tokens Source:** [`src/math_app/presentation/design_system/tokens.py`](../src/math_app/presentation/design_system/tokens.py)  
**Global Stylesheet & KaTeX Renderer:** [`src/math_app/presentation/design_system/styles.py`](../src/math_app/presentation/design_system/styles.py)

---

## 1. Design Principles

1. **One Design System, Multiple Mathematical Workflows:** Every module shares a single visual identity (typography, palette, spacing, cards, action controls, verification badges, and feedback patterns) while keeping the specialized inputs and derivation viewers suited to its mathematics.
2. **Beginner-Friendly & Equation-First by Default:** Workspaces place the equation/expression input (`NHẬP BÀI TOÁN`), essential variables/bounds, example chips, and clear module-specific primary CTA upfront. Both First-Order and Second-Order ODE workspaces detect classification automatically (`PHÂN TÍCH TỰ ĐỘNG`) without forcing learners to pick a classification before typing an equation, while preserving expandable manual overrides (`Đổi phân loại thủ công`).
3. **Three-Level Progressive Disclosure:**
   - **Level 1 — Essential:** Primary input (`NHẬP BÀI TOÁN`), variable/mode/IC controls (`YÊU CẦU BÀI TOÁN`), example chips, primary CTA.
   - **Level 2 — Learning:** Automatic classification summary (`PHÂN TÍCH TỰ ĐỘNG`), canonical forms, expandable classification reasoning (`CƠ SỞ PHÂN LOẠI`), recommended method guidance (`PHƯƠNG PHÁP ĐỀ XUẤT`), step-by-step and 4-stage derivations (actual solution steps remain numbered normally in the Solution Viewer).
   - **Level 3 — Advanced:** Manual ODE classification override drawer, domain restriction panels, branch solutions across singular points, Wronskian/Reduction of Order tools, 2D/3D Plotly charts, variation tables, diagnostic warnings.
4. **Mathematical Precision & Honesty:** Notation distinguishes pointwise inequality ($\neq 0$) from non-identically-zero functions ($g(t) \not\equiv 0$); `VerificationStatus` never overclaims success.

---

## 2. Color Tokens (`AcademicBluePalette`, `NeutralSurfaces`, `SemanticColors`)

| Category | Token | Hex | Contrast / Usage |
|---|---|---|---|
| Primary | `PRIMARY.BLUE_600` | `#2563eb` | Primary CTA buttons, active focus rings |
| Primary Hover | `PRIMARY.BLUE_700` | `#1d4ed8` | Primary hover states |
| Light Accent | `PRIMARY.BLUE_50` | `#eff6ff` | Math icon badges, subtle highlighted panels |
| Canvas | `SURFACES.CANVAS` | `#f8fafc` | Application page background |
| Card | `SURFACES.CARD` | `#ffffff` | Workspace cards, result containers (`border-slate-200`) |
| Main Text | `SURFACES.TEXT_MAIN` | `#0f172a` | 15.8:1 on white (WCAG AAA) |
| Secondary Text | `SURFACES.TEXT_SECONDARY` | `#334155` | 10.3:1 on white (WCAG AAA) |
| Muted Text | `SURFACES.TEXT_MUTED` | `#475569` | 7.58:1 on white (WCAG AAA) |
| Success | `SEMANTIC.SUCCESS` | `#dcfce7` / `#86efac` / `#14532d` | Verified badges (>8:1) |
| Warning | `SEMANTIC.WARNING` | `#fef3c7` / `#fde68a` / `#78350f` | Domain & caution notices (>8:1) |
| Error | `SEMANTIC.ERROR` | `#fee2e2` / `#fecaca` / `#7f1d1d` | Validation & failure alerts (>9:1) |
| Info | `SEMANTIC.INFO` | `#eff6ff` / `#bfdbfe` / `#1e40af` | Domain/order tags (>8:1) |
| Neutral | `SEMANTIC.NEUTRAL` | `#f1f5f9` / `#cbd5e1` / `#1e293b` | Secondary chips & metadata (>9:1) |

Interactive tokens (`INTERACTION`):
- `INTERACTION.FOCUS_RING`: `focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2`
- `INTERACTION.CHIP_SURFACE`: Slate-100 pill surface (`!bg-slate-100 !text-slate-800 border border-slate-300`) — guarantees Quasar never falls back to dark text on Quasar default blue.

---

## 3. Typography (`TYPOGRAPHY`)

- **UI Sans (`FONT_FAMILY_BASE`):** `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif` (100% system-native / zero CDN).
- **Code / Input Mono (`FONT_FAMILY_MONO`):** `'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace`.
- **Math OpenType (`FONT_FAMILY_MATH`):** Local `'DejaVu Math TeX Gyre'` (`/assets/fonts/DejaVuMathTeXGyre.ttf`) + offline KaTeX (`/assets/katex/katex.css`, `/assets/katex/katex.js`).
- **Hierarchy:** `APP_TITLE` (`text-xl md:text-2xl font-black`), `PAGE_TITLE`, `SECTION_HEADING` (`text-sm md:text-base font-bold uppercase tracking-wider`), `BODY_TEXT` (`text-sm`), `FORM_LABEL` (`text-xs font-semibold`).

---

## 4. Spacing, Radii & Elevation (`SPACING`, `RADIUS`, `ELEVATION`)

- **Scale:** 4px increments (`SPACE_1 = 0.25rem` through `SPACE_12 = 3rem`); default form/card spacing `gap-4` (`1rem`) or `gap-5` (`1.25rem`).
- **Border Radius:** Cards `RADIUS.LG` (`rounded-xl`), modals `RADIUS.XL` (`rounded-2xl`), pills `RADIUS.FULL` (`rounded-full`).
- **Elevation:** Rest cards `ELEVATION.SM` / `ELEVATION.XS`; avoid heavy multi-layer shadows or competing bordered gradients inside subcards.

---

## 5. Shared UI Components (`src/math_app/presentation/components/shared/`)

| Symbol | Purpose |
|---|---|
| `get_primary_action_spec(pt)` | Authoritative mapping from all 34 `ProblemType` values to module-specific Vietnamese CTA label, Material icon, and `aria-label`. |
| `render_workspace_header(...)` | Responsive module identity header with KaTeX/Material icon badge, wrapping description, and `status_badge`. |
| `render_example_chips(...)` | High-contrast wrapping `ui.chip(..., color=None)` pills with `mw-example-chip`, `keydown.enter`, and ARIA labels. |
| `primary_button(...)` | Standardized Academic Blue CTA (`min-h-[40px]`, `INTERACTION.FOCUS_RING`, optional `aria_label`). |
| `section_card(...)` | Standardized white surface card (`border-slate-200`, `rounded-xl`, `shadow-sm`). |
| `status_badge(...)` | High-contrast semantic pill badge (`success`, `warning`, `error`, `info`, `neutral`). |
| `render_loading_card(...)` | Centered spinner card with `role="status" aria-live="polite"`. |
| `render_feedback_card(...)` | Semantic alert card with `role="alert"`, Material icon + text (never color alone). |
| `render_empty_state_card(...)` | Subtle neutral empty-state card. |

Shell components: `create_page_shell()`, `render_app_header()`, `render_sticky_nav_bar()`, `render_back_button()`, `render_footer()`.

---

## 6. Input Standards

- **Expression / Equation Inputs:** Full width (`w-full`) on mobile, monospace font (`font-mono`), clear Vietnamese labels and concrete placeholders.
- **Variable Inputs:** Label `"Biến số"` with responsive `w-full sm:w-36` alongside `render_adaptive_variable_selector()` so labels never truncate.
- **Parameter & Bound Groups:** Always use `flex-wrap` rows with mobile-full / desktop-fixed widths (`w-full sm:w-52`, `w-28 sm:w-24`).
- **Stale State Rule:** Any change to equation/expression, variable, parameter, or example chip immediately clears `results_container`; async submit locks the primary action button while running and restores it in `finally`.

---

## 7. Result Presentation Standard

`render_solution_view()` renders a predictable top-to-bottom hierarchy:
1. Result card title + honest verification badge (`render_verification_badge()`).
2. `ĐỀ CHO:` normalized problem statement (`problem_statement.py`).
3. ODE Classification & Method card (when applicable for Second-Order / Euler–Cauchy).
4. `ĐÁP SỐ CUỐI CÙNG:` visually emphasized Academic Blue answer block with `.math-scroll-box`.
5. `Điều kiện xác định của bài toán:` (`domain_view.py`) and Branch Solutions (`render_branch_solutions()`).
6. Filtered algorithm warnings / diagnostics.
7. Contextual visualization tools (`Vẽ đồ thị 2D`, `Vẽ đồ thị 3D`, `Bảng biến thiên` — strictly disabled for Matrix ops).
8. Detailed derivation viewer:
   - `step_viewer.py` (Simple Step-by-Step; suppresses duplicate `Kết luận:` card on 1-step results).
   - `ode_staged_step_viewer.py` (4-Stage Pedagogical Flow for ODEs with `Mở rộng tất cả` / `Thu gọn tất cả`).

---

## 8. Verification Presentation

`render_verification_badge()` enforces:
- Green verified badge (`✓ Đã kiểm chứng toán học` / `✓ Kiểm chứng nối trơn C¹`) ONLY when `has_valid_result=True` and verifier confirmed.
- Distinct icon + prefix text (`✓`, `⚠`, `✗`) alongside semantic colors for `FAILED`, `PARTIALLY_VERIFIED`, `CONDITIONAL_EXTENSION`, and `UNVERIFIED` plus `role="status"` and hover tooltips.

---

## 9. Responsive Rules (360px – 1440px)

- `.mw-page-shell` uses `max-w-7xl mx-auto` with mobile padding override (`0.65rem` at `<= 640px`).
- All `.nicegui-row`, `.nicegui-column`, `.q-card`, `.q-field` enforce `min-width: 0; max-width: 100%`.
- `.mw-example-chip` sets `height: auto; white-space: normal; overflow-wrap: anywhere` so long Vietnamese equations wrap cleanly on `360px`/`390px` screens without horizontal page overflow.
- `.math-scroll-box` enforces `overflow-x: auto; overflow-y: hidden` so tall fractions scroll horizontally if ever wider than viewport without vertical scrollbar clutter.

---

## 10. Accessibility Standards

- Global `:focus-visible` outline (`2px solid #2563eb`, `offset: 2px`) across buttons, links, inputs, chips, and `[role="button"]`.
- Explicit `aria-label` attributes on header About button, Back button, Reset/Clear controls, Primary CTA buttons, Catalog cards (`role="button" tabindex="0"` + Enter/Space), and plot toolbar buttons (no raw emoji-only actions).
- Status/alert semantics (`role="status"`, `role="alert"`, `aria-expanded`) and non-color-only icons across every feedback state.

---

## 11. Guidelines for Adding a New Mathematical Module

1. Add the `ProblemType` enum member in `domain/models.py` (updating `is_matrix` / `is_ode` sets if applicable).
2. Add the solver/verifier/parser behind `SolveProblemUseCase` (strictly keeping `domain`, `input`, `solvers`, `verification` independent of NiceGUI/Plotly).
3. Register its `OperationDef` in `operation_catalog.py` (default input, variable, `examples`, `math_icon`, `is_menu_card`).
4. Add an explicit `PrimaryActionSpec` entry in `components/shared/action_labels.py`.
5. Compose the input UI using `render_workspace_header()`, `render_example_chips()`, `primary_button()`, `render_loading_card()`, and `render_feedback_card()`; clear `results_container` on input/parameter edits.
6. Add presentation tests covering button label accuracy, valid/invalid submission, and responsive rendering.
