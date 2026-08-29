import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#f5f5f7",
        foreground: "#1d1d1f",
        card: "#ffffff",
        muted: "#f5f5f7",
        border: "#d2d2d7",
        accent: "#0071e3",
        copper: "#0077ed",
        danger: "#de3b2f",
        warn: "#b75106",
        ok: "#248a3d",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Inter", "system-ui", "sans-serif"],
        display: ["var(--font-sans)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "IBM Plex Mono", "monospace"],
      },
      borderRadius: {
        DEFAULT: "12px",
      },
    },
  },
  plugins: [],
};

export default config;
