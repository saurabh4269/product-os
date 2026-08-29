import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#020617",
        foreground: "#F8FAFC",
        card: "#0E1223",
        muted: "#1A1E2F",
        border: "#334155",
        accent: "#16A34A",
        danger: "#DC2626",
        warn: "#D97706",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Fira Sans", "sans-serif"],
        mono: ["var(--font-mono)", "Fira Code", "monospace"],
      },
      boxShadow: {
        glow: "0 0 24px rgba(22,163,74,0.25)",
      },
    },
  },
  plugins: [],
};

export default config;
