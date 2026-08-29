import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#f6f9fc",
        foreground: "#0a2540",
        card: "#ffffff",
        muted: "#f0f4f8",
        border: "#e6ebf1",
        accent: "#635bff",
        copper: "#7a73ff",
        danger: "#df1b41",
        warn: "#c2410c",
        ok: "#0d9488",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Inter", "sans-serif"],
        display: ["var(--font-sans)", "Inter", "sans-serif"],
        mono: ["var(--font-mono)", "IBM Plex Mono", "monospace"],
      },
      borderRadius: {
        DEFAULT: "8px",
      },
    },
  },
  plugins: [],
};

export default config;
