/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0a0c10",
        foreground: "#f0f6fc",
        card: "#12151d",
        cardBorder: "#212631",
        accent: {
          blue: "#388bfd",
          cyan: "#39c5cf",
          green: "#2ea043",
          yellow: "#d29922",
          red: "#f85149",
          purple: "#a371f7",
        }
      },
    },
  },
  plugins: [],
};
