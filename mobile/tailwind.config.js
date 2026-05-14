/** @type {import('tailwindcss').Config} */

module.exports = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,jsx,ts,tsx}",
    "./components/**/*.{js,jsx,ts,tsx}",
  ],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#FBF4E8",
          100: "#F5E6CC",
          200: "#E5CBA0",
          300: "#D1AC72",
          400: "#B8904F",
          500: "#8B6F47", // caramel accent (was indigo)
          600: "#6F5538",
          700: "#5A4429",
          800: "#3D2914",
          900: "#2B1810",
        },

        // Reverse-mapped: high numbers used to be the *darkest* shades
        // (backgrounds in a dark theme). They now map to the *lightest*
        // shades (backgrounds in a light theme). The scale still reads
        // "low = light text, high = dark surface", just inverted in
        // brightness so component classnames Just Work.
        dark: {
          50: "#1F100B", // deepest espresso (was lightest gray)
          100: "#2B1810",
          200: "#3D2914",
          300: "#5A4429", // body text (used on cream surfaces)
          400: "#6F5538", // muted body
          500: "#8B6F47", // tertiary text / placeholders
          600: "#B89972", // hover borders
          700: "#D4C5B0", // borders / dividers
          800: "#E8DDCB", // card / chip background
          900: "#F5EFE6", // main app background (cream)
          950: "#FBF6EE", // even lighter surface
        },

        accent: {
          pink: "#D08B7A",      // dusty rose
          purple: "#C97B5D",    // terracotta (was deep purple)
          teal: "#7A9B8A",      // sage
          orange: "#D89060",    // warm amber
        },
      },
      fontFamily: {
        // Body text -- elegant readable serif. Loaded from
        // @expo-google-fonts/lora in app/_layout.tsx.
        sans: ["Lora_400Regular", "Georgia", "serif"],
        body: ["Lora_400Regular", "serif"],
        // Display headings -- high-contrast classic serif.
        // Loaded from @expo-google-fonts/playfair-display.
        display: ["PlayfairDisplay_700Bold", "Georgia", "serif"],
        serif: ["PlayfairDisplay_600SemiBold", "Georgia", "serif"],
      },
    },
  },
  plugins: [],
};
