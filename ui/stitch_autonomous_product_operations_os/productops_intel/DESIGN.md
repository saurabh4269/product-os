---
name: ProductOps Intel
colors:
  surface: '#fcf8fa'
  surface-dim: '#dcd9db'
  surface-bright: '#fcf8fa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f5'
  surface-container: '#f0edef'
  surface-container-high: '#eae7e9'
  surface-container-highest: '#e4e2e4'
  on-surface: '#1b1b1d'
  on-surface-variant: '#45464d'
  inverse-surface: '#303032'
  inverse-on-surface: '#f3f0f2'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#4648d4'
  on-secondary: '#ffffff'
  secondary-container: '#6063ee'
  on-secondary-container: '#fffbff'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#271901'
  on-tertiary-container: '#98805d'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#e1e0ff'
  secondary-fixed-dim: '#c0c1ff'
  on-secondary-fixed: '#07006c'
  on-secondary-fixed-variant: '#2f2ebe'
  tertiary-fixed: '#fcdeb5'
  tertiary-fixed-dim: '#dec29a'
  on-tertiary-fixed: '#271901'
  on-tertiary-fixed-variant: '#574425'
  background: '#fcf8fa'
  on-background: '#1b1b1d'
  surface-variant: '#e4e2e4'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  container-padding: 24px
  gutter: 16px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style

The design system is anchored in **Sophisticated Technical Trust**. It targets high-level Product Operations teams and engineers who require high-density data visualization without cognitive fatigue. The aesthetic is **Corporate Modern** with a **Minimalist** lean, prioritizing utility, precision, and clarity.

The visual narrative centers on "Technical Transparency." Every AI-generated insight or agent action is framed with clear provenance and logic trails. The interface uses a layered architecture to separate raw data logs from high-level strategic signals, ensuring the user feels in control of the underlying machine learning processes.

**Key Brand Pillars:**
*   **Architectural Precision:** Every pixel serves a structural purpose.
*   **Operational Clarity:** Statuses are immediate; ambiguity is eliminated.
*   **Quiet Intelligence:** The UI recedes to let the data and insights lead.

## Colors

The palette is designed for prolonged professional use, utilizing a "Slate" foundation to reduce eye strain.

*   **Primary (Deep Intelligence Blue):** Used for core navigation, high-level headers, and text to establish authority.
*   **Active Indigo:** Reserved for interactive elements, primary call-to-actions, and "active" agent states.
*   **Semantic Accents:** Emerald and Amber are used strictly for status signaling—green for verified fixes and successful deployments, amber for diagnostic warnings and signals requiring attention.
*   **Surfaces:** A multi-tier gray scale creates a sense of depth and hierarchy, separating the main canvas from sidebar controls and utility panels.

## Typography

This design system utilizes **Inter** for its neutral, highly legible character, essential for complex enterprise dashboards. To support the "Technical Transparency" narrative, **JetBrains Mono** is introduced for data sources, code snippets, and raw log outputs.

**Hierarchy Rules:**
*   **Display & Headlines:** Use tight letter-spacing and semi-bold weights to maintain a structured, professional appearance.
*   **Body Copy:** Stick to 14px for standard UI text to maximize information density while maintaining readability.
*   **Labels:** Use the "label-caps" style for section headers within panels and sidebar categories to create clear visual separation.
*   **Monospaced Data:** Always use `code-sm` for references to GitHub commits, BigQuery table names, or specific API endpoints.

## Layout & Spacing

The layout utilizes a **Fluid Grid** model with fixed-width sidebars. The system is built on a 4px base unit to ensure precise alignment of dense data components.

*   **Grid Model:** 12-column grid for the main content area. Sidebars (Navigation and Inspection) are fixed at 240px and 360px respectively.
*   **Responsive Reflow:** 
    *   **Desktop (1280px+):** Full three-pane layout (Nav, Canvas, Inspector).
    *   **Tablet (768px - 1279px):** Inspector panel collapses into a modal or overlay; grid shifts to 8 columns.
    *   **Mobile (<767px):** Single-column stack; sidebars accessible via hamburger/drawer.
*   **Rhythm:** Use `stack-md` (16px) for most vertical relationships between cards and inputs. Use `stack-sm` (8px) for related metadata groups.

## Elevation & Depth

Hierarchy is established through **Tonal Layering** supplemented by **Low-contrast outlines**. This system avoids heavy shadows to maintain a clean, technical look.

*   **Level 0 (Background):** Surface Primary (#F8FAFC). The main canvas area.
*   **Level 1 (Cards/Panels):** Pure White (#FFFFFF) with a 1px border of Slate-200 (#E2E8F0). Used for primary content blocks.
*   **Level 2 (Dropdowns/Modals):** Pure White with a subtle, diffused ambient shadow (Blur: 12px, Opacity: 0.05, Color: #0F172A).
*   **Interactions:** Hover states on interactive cards should use a subtle Indigo-50 (#EEF2FF) tint rather than a shadow increase.

## Shapes

The shape language is "Soft" (4px corners), striking a balance between the rigidity of a technical tool and the modern accessibility of a SaaS product.

*   **Components:** Buttons, Input fields, and Chips use a consistent 4px (`rounded-md`) radius.
*   **Containers:** Large layout sections and main dashboard cards use 8px (`rounded-lg`) to provide a subtle structural container.
*   **Special Elements:** Status indicators (Verify/Signal) use a full pill shape to distinguish them from functional buttons.

## Components

### Buttons & Inputs
*   **Primary Button:** Deep Blue (#0F172A) background with White text. Bold, authoritative.
*   **Active Button:** Active Indigo (#6366F1) for primary actions within a workflow (e.g., "Run Analysis").
*   **Input Fields:** Ghost-style borders (#E2E8F0) that thicken and turn Indigo on focus. Use JetBrains Mono for placeholder text in technical search fields.

### Chips & Indicators
*   **Status Chips:** Use a subtle background tint (e.g., Emerald-50) with high-contrast text (Emerald-700) and a leading dot icon to indicate "Verify" or "Fix" stages.
*   **Source Tags:** Small, monochromatic tags showing the logo of the data source (GitHub, BigQuery) to provide context for AI reasoning.

### Data Cards
*   **Modular Construction:** Cards should have a header (Title + Source), Body (Data/Visualization), and Footer (Timestamp + Confidence Score).
*   **Agent Flow Components:** Use directional connectors (1px dashed lines) between cards to visualize the "Agent Communication Flow."

### Checkboxes & Radio Buttons
*   Custom-styled Indigo square/circle with a white inner-check. Avoid default browser styling to maintain the "Technical Trust" aesthetic.

### Additional Components
*   **Reasoning Accordion:** A specialized component that expands to show the raw thought process of the AI agent, using monospaced typography.
*   **Data Embedding Blocks:** High-density mini-charts (sparklines) embedded directly within list items to show trend signals without opening full reports.