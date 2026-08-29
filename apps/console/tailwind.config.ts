import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#100e14",
        foreground: "#f6f0e6",
        card: "#1a1620",
        muted: "#221c2b",
        border: "rgba(246,240,230,0.08)",
        accent: "#ff7a45",
        copper: "#ffb089",
        danger: "#ff5a6a",
        warn: "#e8c36a",
        ok: "#6fbf93",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Outfit", "sans-serif"],
        display: ["var(--font-display)", "Instrument Serif", "serif"],
        mono: ["var(--font-mono)", "IBM Plex Mono", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
