import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Dark by default - SPECIFICATIONS.MD Sec 26, for gym use.
        ink: { DEFAULT: "#e8eaed", dim: "#9aa0a6", faint: "#5f6368" },
        surface: { DEFAULT: "#101114", raised: "#181a1f", edge: "#24262c" },
        accent: { DEFAULT: "#7dd3a0", dim: "#3f6b52" },
        warn: "#e8a33d",
        bad: "#e5646a",
      },
      minHeight: { tap: "44px" },
      minWidth: { tap: "44px" },
    },
  },
  plugins: [],
} satisfies Config;
