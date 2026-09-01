---
name: Lumina Systems
colors:
  surface: '#f9f9ff'
  surface-dim: '#d8d9e5'
  surface-bright: '#f9f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f3fe'
  surface-container: '#ecedf9'
  surface-container-high: '#e6e8f3'
  surface-container-highest: '#e0e2ed'
  on-surface: '#181c23'
  on-surface-variant: '#414755'
  inverse-surface: '#2d3039'
  inverse-on-surface: '#eef0fc'
  outline: '#717786'
  outline-variant: '#c1c6d7'
  surface-tint: '#005bc1'
  primary: '#0058bc'
  on-primary: '#ffffff'
  primary-container: '#0070eb'
  on-primary-container: '#fefcff'
  inverse-primary: '#adc6ff'
  secondary: '#4a47d2'
  on-secondary: '#ffffff'
  secondary-container: '#6462ec'
  on-secondary-container: '#fffbff'
  tertiary: '#9e3d00'
  on-tertiary: '#ffffff'
  tertiary-container: '#c64f00'
  on-tertiary-container: '#fffbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a41'
  on-primary-fixed-variant: '#004493'
  secondary-fixed: '#e2dfff'
  secondary-fixed-dim: '#c2c1ff'
  on-secondary-fixed: '#0c006b'
  on-secondary-fixed-variant: '#332dbc'
  tertiary-fixed: '#ffdbcc'
  tertiary-fixed-dim: '#ffb595'
  on-tertiary-fixed: '#351000'
  on-tertiary-fixed-variant: '#7c2e00'
  background: '#f9f9ff'
  on-background: '#181c23'
  surface-variant: '#e0e2ed'
  surface-high: '#FFFFFF'
  surface-base: '#F5F5F7'
  surface-subtle: '#E5E5EA'
  accent-success: '#34C759'
  accent-warning: '#FF9500'
  accent-error: '#FF3B30'
  text-primary: '#1D1D1F'
  text-secondary: '#86868B'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 17px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-md:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.02em
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.06em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  margin-sm: 16px
  margin-md: 24px
  margin-lg: 40px
  gutter: 24px
  container-max: 1440px
---

## Brand & Style

The design system is centered on **Empathetic Intelligence**. It bridges the gap between complex operational data and human-centric decision-making, drawing inspiration from the refined minimalism of premium consumer ecosystems. The style is **Corporate Modern** with a **Glassmorphism** influence, prioritizing high-contrast clarity, soft edges, and an approachable technical presence.

The visual narrative shifts from "showing the machine's work" to "conversing with a partner." It leverages generous whitespace to reduce cognitive load and uses depth to create a focused, calm environment for high-stakes product operations.

**Key Brand Pillars:**
*   **Human-Centricity:** Interfaces that feel conversational and warm rather than clinical.
*   **Intuitive Depth:** Using layers and soft shadows to guide focus naturally.
*   **Refined Clarity:** Removing visual noise to highlight what truly matters.

## Colors

This design system uses a high-contrast, clean palette that emphasizes "Surface over Line." The default mode is **Light**, utilizing pure white elevations against soft gray foundations to create a sense of physical layering.

*   **Primary (Apple Blue):** Used for primary actions, selection states, and meaningful links. It provides a familiar, trusted anchor for interactivity.
*   **Secondary (Google Indigo):** Used for specialized logic trails and "thinking" states to distinguish human actions from system processes.
*   **Surfaces:** 
    *   **Surface High:** Pure white, used for the main interactive cards and content containers.
    *   **Surface Base:** A very light gray (#F5F5F7) used for the background to make white cards "pop."
*   **Accents:** Vibrancy is used sparingly for status signaling. Success, warning, and error colors are pulled from established accessible standards to ensure immediate recognition.

## Typography

The typography system relies on **Inter**, configured with generous tracking and optical sizing to mimic the legibility of SF Pro.

**Hierarchy & Voice:**
*   **Humanized Labels:** Use `body-lg` for narrative status updates (e.g., "Sarah is analyzing the logs...") to create a person-first experience.
*   **Legibility:** Line heights are intentionally loose to prevent "text-wall" fatigue in dense data environments.
*   **Tracking:** Larger headlines use negative tracking for a premium, tight feel, while small labels use increased letter spacing to ensure readability at a glance.
*   **Scale:** The system transitions from a 15px base for standard body text to 17px for narrative-heavy sections, prioritizing comfort over density.

## Layout & Spacing

The layout follows a **Fluid Grid** philosophy with expanded margins to allow the UI to "breathe." It moves away from rigid borders toward layout-driven separation.

*   **Grid System:** A 12-column grid for desktop, reducing to 8 for tablet and 4 for mobile.
*   **Whitespace:** Use `margin-lg` (40px) between major logical sections. Internal card padding should never drop below 24px to maintain an open feel.
*   **Borders:** Borders are minimized. Where necessary, use 1px `surface-subtle` colors. Separation should primarily be achieved through background color shifts and soft shadows.
*   **Breakpoints:**
    *   **Desktop:** 1200px+ (Standard 12-column).
    *   **Tablet:** 768px - 1199px (Fixed sidebars become collapsible).
    *   **Mobile:** < 768px (Full-width cards, 16px horizontal margins).

## Elevation & Depth

Hierarchy is established using **Ambient Shadows** and **Tonal Layers**. This creates a physical "stack" where the most actionable items appear closest to the user.

*   **Level 0 (Base):** `surface-base` (#F5F5F7). The digital floor.
*   **Level 1 (Cards):** Pure white with a very soft, large-radius shadow (Y: 4px, Blur: 20px, Color: rgba(0,0,0,0.04)). This is the standard container for all content.
*   **Level 2 (Modals/Popovers):** Pure white with a more pronounced shadow (Y: 10px, Blur: 30px, Color: rgba(0,0,0,0.08)) and a 1px soft outline.
*   **Glassmorphism:** Navigation bars and top headers should use a backdrop-filter (blur: 20px) with 80% opacity to maintain context of the content scrolling beneath them.

## Shapes

The shape language is highly approachable and friendly, using significant rounding to soften the technical nature of the tool.

*   **Cards & Containers:** Utilize `rounded-2xl` (1rem) as the standard. For large dashboard containers, `rounded-3xl` (1.5rem) is preferred to create a soft, "island" aesthetic.
*   **Interactive Elements:** Buttons and input fields use `rounded-lg` (1rem) to match the container curves.
*   **Status Indicators:** Chips and tags use a full pill shape for maximum differentiation from square-ish data cells.

## Components

### Buttons
*   **Primary:** Solid `primary-color` with white text. High-contrast, rounded-pill or `rounded-lg`.
*   **Secondary:** Ghost style with a subtle `surface-subtle` background. No border.

### Inputs & Fields
*   **Style:** Filled backgrounds (`surface-subtle`) that transition to white with a primary-colored glow on focus.
*   **Labels:** Labels should be placed inside the field or as "Natural Language" prompts above the field.

### Cards
*   **Narrative Cards:** Used for AI insights. These should lead with a human-centric title (e.g., "What I found in the logs") and use `body-lg` for the description.
*   **Actionable Cards:** Feature a clear footer with a single primary action, separated by a very faint 1px line.

### Chips & Lists
*   **Status Chips:** Use soft, pastel backgrounds with dark text (e.g., light green background with dark green text) to indicate status without being aggressive.
*   **Lists:** List items should have generous vertical padding (16px+) and use `rounded-lg` hover states.

### Checkboxes & Radios
*   Use standard iOS/Material-inspired sizing (20px-24px) with smooth spring animations for transitions. Primary color for "on" states.

### Voice & Tone
*   **Labels:** Avoid jargon. Instead of "Fetch Data," use "Get the latest info." Instead of "Agent Reasoning," use "How I reached this conclusion."