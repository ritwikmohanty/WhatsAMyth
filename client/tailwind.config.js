export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        "bg-primary": "#0a0a0f",
        "bg-secondary": "#12121a",
        "bg-card": "#1a1a24",
        "bg-input": "#0f0f16",
        "text-primary": "#f0f0f5",
        "text-secondary": "#9090a0",
        "text-muted": "#606070",
        "accent-green": "#00d67d",
        "accent-green-dim": "#00a060",
        "accent-red": "#ff4757",
        "accent-red-dim": "#c0354a",
        "accent-yellow": "#ffc107",
        "accent-blue": "#3b82f6",
      },
      fontFamily: {
        // Poppins first so it's used by default; fallback to DM Sans and system fonts
        sans: ["Poppins", "DM Sans", "system-ui", "sans-serif"],
        serif: ["Fraunces", "serif"],
      },
      gridTemplateColumns: {
        "auto-fit": "repeat(auto-fit, minmax(150px, 1fr))",
      },
      zIndex: {
        100: "100",
        50: "50",
      },
    },
  },
  plugins: [],
}
