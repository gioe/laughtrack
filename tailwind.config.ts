import { heroui } from "@heroui/theme";
import type { Config } from "tailwindcss";
import daisyui from "daisyui";
import withMT from "@material-tailwind/react/utils/withMT";

// Color definitions
const baseColors = {
    transparent: "transparent",
    current: "currentColor",
    white: "#ffffff",
    purple: "#3f3cbb",
    midnight: "#121063",
    metal: "#565584",
    tahiti: "#3ab7bf",
    silver: "#ecebff",
    "bubble-gum": "#ff77e9",
    bermuda: "#78dcca",
};

const brandColors = {
    "navy-blue": "#003366",
    "rose-gold": "#B76E79",
    "silver-gray": "#C0C0C0",
    shark: "#1C232A",
    "brown-rust": "#B95D3B",
    "sandy-brown": "#F6916C",
    kelp: "#474838",
    ivory: "#FFFFF0",
    paarl: "#A96030",
    cedar: "#361E14",
    "coconut-cream": "#FAF6E0",
    locust: "#acae89",
    "pine-tree": "#232604",
    skeptic: "#9eb4aa",
    "ecru-white": "#fafaf0",
    juniper: "#72908e",
    "tax-break": "#4c6b73",
    madison: "#2f4858",
    "american-silver": "#ced9cb",
    "midnight-blue": "#003366",
    copper: "#B87333",
    "soft-charcoal": "#4A4A4A",
    champagne: "#F7E7CE",
};

const themeColors = {
    background: "hsl(var(--background))",
    foreground: "hsl(var(--foreground))",
    card: {
        DEFAULT: "hsl(var(--card))",
        foreground: "hsl(var(--card-foreground))",
    },
    popover: {
        DEFAULT: "hsl(var(--popover))",
        foreground: "hsl(var(--popover-foreground))",
    },
    primary: {
        DEFAULT: "hsl(var(--primary))",
        foreground: "hsl(var(--primary-foreground))",
    },
    secondary: {
        DEFAULT: "hsl(var(--secondary))",
        foreground: "hsl(var(--secondary-foreground))",
    },
    muted: {
        DEFAULT: "hsl(var(--muted))",
        foreground: "hsl(var(--muted-foreground))",
    },
    accent: {
        DEFAULT: "hsl(var(--accent))",
        foreground: "hsl(var(--accent-foreground))",
    },
    destructive: {
        DEFAULT: "hsl(var(--destructive))",
        foreground: "hsl(var(--destructive-foreground))",
    },
    border: "hsl(var(--border))",
    input: "hsl(var(--input))",
    ring: "hsl(var(--ring))",
    chart: {
        "1": "hsl(var(--chart-1))",
        "2": "hsl(var(--chart-2))",
        "3": "hsl(var(--chart-3))",
        "4": "hsl(var(--chart-4))",
        "5": "hsl(var(--chart-5))",
    },
};

const fonts = {
    sans: ['"PT Sans"', "sans-serif"],
    "gilroy-regular": ['"Gilroy-Regular"', "sans-serif"],
    "gilroy-medium": ['"Gilroy-Medium"', "sans-serif"],
    "gilroy-light": ['"Gilroy-Light"', "sans-serif"],
    "gilroy-heavy": ['"Gilroy-Heavy"', "sans-serif"],
    "gilroy-bold": ['"Gilroy-Bold"', "sans-serif"],
    bebas: "var(--font-bebas)",
    oswald: "var(--font-oswald)",
    fjalla: "var(--font-fjalla)",
    dmSans: "var(--font-dmSans)",
    chivo: "var(--font-chivo)",
    inter: "var(--font-inter)",
    outfit: "var(--font-outfit)",
};

const config: Config = {
    darkMode: ["class"],
    relative: true,
    content: [
        "./ui/components/**/*.{js,ts,jsx,tsx}",
        "./ui/pages/**/*.{js,ts,jsx,tsx}",
        "./app/**/*.{js,ts,jsx,tsx}",
        "./node_modules/@nextui-org/theme/dist/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        screens: {
            '2xs': { min: '300px' },
            xs: { max: '575px' }, // Mobile (iPhone 3 - iPhone XS Max).
            sm: { min: '576px', max: '897px' }, // Mobile (matches max: iPhone 11 Pro Max landscape @ 896px).
            md: { min: '898px', max: '1199px' }, // Tablet (matches max: iPad Pro @ 1112px).
            lg: { min: '1200px' }, // Desktop smallest.
            xl: { min: '1259px' }, // Desktop wide.
            '2xl': { min: '1359px' } // Desktop widescreen.
          },
        extend: {
                   spacing: {
                     '18': '4.5rem',
                     '22': '5.5rem',
                     '72': '18rem',
                     '84': '21rem',
                     '96': '24rem',
                   },
            keyframes: {
                pulse: {
                    "0%, 100%": { opacity: "1" },
                    "50%": { opacity: "0.5" },
                },
                fadeIn: {
                    "0%": { opacity: "0" },
                    "100%": { opacity: "1" }
                },
                slideUp: {
                    "0%": { transform: "translateY(10px)", opacity: "0" },
                    "100%": { transform: "translateY(0)", opacity: "1" }
                }
            },
            animation: {
                pulse: "pulse 2s ease-in-out infinite",
                fadeIn: "fadeIn 0.3s ease-in-out",
                slideUp: "slideUp 0.4s ease-out"
            },
            fontFamily: fonts,
            colors: {
                ...baseColors,
                ...brandColors,
                ...themeColors,
            },
            borderRadius: {
                lg: "var(--radius)",
                md: "calc(var(--radius) - 2px)",
                sm: "calc(var(--radius) - 4px)",
            },
        },
    },
    variants: {
        fill: ["hover", "focus"],
    },
    plugins: [
        daisyui,
        heroui(),
        require("@tailwindcss/forms"),
    ],
};

export default withMT(config);
