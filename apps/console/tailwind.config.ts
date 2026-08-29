import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#08090a",
        foreground: "#ececee",
        card: "#111113",
        muted: "#18181b",
        border: "rgba(255,255,255,0.08)",
        accent: "#5e6ad2",
        copper: "#d4a27f",
        danger: "#eb5757",
        warn: "#e2a03f",
        ok: "#4cb782",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "IBM Plex Sans", "sans-serif"],
        mono: ["var(--font-mono)", "IBM Plex Mono", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(94,106,210,0.35), 0 12px 40px rgba(0,0,0,0.45)",
      },
      borderRadius: {
        xl: "12px",
      },
    },
  },
  plugins: [],
};

export default config;
