import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#152025",
        paper: "#f6f3ed",
        panel: "#fffaf1",
        line: "#d9d1c3",
        jade: "#23766b",
        persimmon: "#c45f36",
        cobalt: "#315d9f"
      },
      boxShadow: {
        panel: "0 18px 60px rgba(21, 32, 37, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;
