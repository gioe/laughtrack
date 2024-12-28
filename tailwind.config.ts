import { nextui } from "@nextui-org/theme";
import type { Config } from "tailwindcss";
import daisyui from "daisyui";
import withMT from "@material-tailwind/react/utils/withMT";

const config: Config = {
    darkMode: ["class"],
    relative: true,
    content: [
        './components/**/*.{js,ts,jsx,tsx}"',
        './app/**/*.{js,ts,jsx,tsx}"',
        "./node_modules/@nextui-org/theme/dist/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['"PT Sans"', "sans-serif"],
                bebas: "var(--font-bebas)",
                oswald: "var(--font-oswald)",
                fjalla: "var(--font-fjalla)",
                inter: "var(--font-inter)"
            },
            colors: {
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
                "navy-blue": "#003366",
                "rose-gold": "#B76E79",
                "silver-gray": "#C0C0C0",
                shark: "#1C232A",
                ivory: "#FFFFF0",
                "midnight-blue": "#003366",
                copper: "#B87333",
                "soft-charcoal": "#4A4A4A",
                champagne: "#F7E7CE",
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
            },
            borderRadius: {
                lg: "var(--radius)",
                md: "calc(var(npm-radius) - 2px)",
                sm: "calc(var(--radius) - 4px)",
            },
        },
    },
    variants: {
        fill: ["hover", "focus"],
    },
    plugins: [daisyui, nextui(), require("@tailwindcss/forms")],
};

export default withMT(config);
