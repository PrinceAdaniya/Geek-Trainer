import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-body)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Impact", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      colors: {
        // YOUR GYM palette: deep indigo ground, hot pink lead, with orange,
        // yellow, cyan and violet for the gradient and category colour.
        ink: { DEFAULT: "#f5f3ff", dim: "#b9b3d9", faint: "#8580ab" },
        surface: { DEFAULT: "#0e0b1f", raised: "#181430", edge: "#2d2754" },
        accent: { DEFAULT: "#ff4d8d", dim: "#7d2a4c" },
        brand: {
          pink: "#ff4d8d",
          orange: "#ff8a3d",
          yellow: "#ffd23f",
          cyan: "#2ee6d6",
          violet: "#8b5cf6",
          lime: "#b6f36a",
        },
        info: "#6ba9ff",
        warn: "#fbbf24",
        bad: "#f87171",
        // Sequential single-hue ramp for the training heatmap. Validated:
        // monotone lightness, adjacent gaps >= 0.06, light end clears the
        // surface. Magnitude, not identity - see api/app/core/ranks.py.
        heat: {
          0: "#231e42",
          1: "#5a1f45",
          2: "#8a2a5e",
          3: "#c23a78",
          4: "#f25897",
          5: "#ffa3c8",
        },
      },
      minHeight: { tap: "44px" },
      minWidth: { tap: "44px" },
      keyframes: {
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
        aura: {
          "0%,100%": { opacity: "0.55", transform: "scale(1)" },
          "50%": { opacity: "0.9", transform: "scale(1.04)" },
        },
        chargeIn: {
          "0%": { opacity: "0", transform: "scale(0.9)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        sweep: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(400%)" },
        },
      },
      animation: {
        marquee: "marquee 28s linear infinite",
        aura: "aura 2.4s ease-in-out infinite",
        chargeIn: "chargeIn 320ms cubic-bezier(0.2, 0.9, 0.3, 1)",
        sweep: "sweep 2.6s linear infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
