import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      colors: {
        ink: { DEFAULT: "#e8eaed", dim: "#9aa0a6", faint: "#5f6368" },
        surface: { DEFAULT: "#0b0c0f", raised: "#131519", edge: "#23262d" },
        accent: { DEFAULT: "#7dd3a0", dim: "#3f6b52" },
        info: "#6ba9ff",
        warn: "#fbbf24",
        bad: "#f87171",
        // Sequential single-hue ramp for the training heatmap. Validated:
        // monotone lightness, adjacent gaps >= 0.06, light end clears the
        // surface. Magnitude, not identity - see api/app/core/ranks.py.
        heat: {
          0: "#181a1f",
          1: "#2a5546",
          2: "#356f57",
          3: "#44916d",
          4: "#57bb8d",
          5: "#8ee9bd",
        },
      },
      minHeight: { tap: "44px" },
      minWidth: { tap: "44px" },
      keyframes: {
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
        aura: "aura 2.4s ease-in-out infinite",
        chargeIn: "chargeIn 320ms cubic-bezier(0.2, 0.9, 0.3, 1)",
        sweep: "sweep 2.6s linear infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
