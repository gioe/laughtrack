import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/util/tailwindUtil";

const buttonVariants = cva(
    `inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm
   font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring
    disabled:pointer-events-none disabled:opacity-50`,
    {
        variants: {
            variant: {
                default:
                    "bg-primary text-primary-foreground shadow hover:bg-primary/90",
                destructive:
                    "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
                outline:
                    "border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground",
                secondary:
                    "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80",
                ghost: "hover:bg-accent hover:text-accent-foreground",
                link: "text-primary underline-offset-4 hover:underline",
                roundedShimmer: [
                    "relative overflow-hidden",
                    "rounded-lg text-white font-bold font-dmSans",
                    "bg-copper shadow-sm",
                    "transform transition-all duration-200 ease-in-out",
                    "hover:shadow-md hover:-translate-y-[1px] hover:scale-[1.02]",
                    "active:translate-y-[1px] active:scale-[0.98]",
                    "disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:scale-100",
                    "before:absolute before:inset-0 before:bg-white/20",
                    "before:translate-x-[-100%] before:hover:translate-x-[100%]",
                    "before:transition-transform before:duration-500",
                ].join(" "),
                roundedShimmerOutline: [
                    "rounded-lg border-2 border-copper bg-transparent",
                    "text-copper font-bold font-dmSans",
                    "transition-colors",
                    "hover:bg-copper hover:text-white",
                    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper focus-visible:ring-0",
                ].join(" "),
            },
            size: {
                default: "h-9 px-4 py-2",
                sm: "h-8 rounded-md px-3 text-xs",
                lg: "h-10 rounded-md px-8",
                icon: "h-9 w-9",
                roundedShimmer: "h-auto px-6 py-2.5 text-body",
                roundedShimmerOutline: "h-auto px-6 py-3 text-body",
            },
        },
        defaultVariants: {
            variant: "default",
            size: "default",
        },
        compoundVariants: [
            {
                variant: "roundedShimmer",
                size: "default",
                className: "h-auto px-6 py-2.5 text-body",
            },
            {
                variant: "roundedShimmerOutline",
                size: "default",
                className: "h-auto px-6 py-3 text-body",
            },
        ],
    },
);

export interface ButtonProps
    extends React.ButtonHTMLAttributes<HTMLButtonElement>,
        VariantProps<typeof buttonVariants> {
    asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant, size, asChild = false, ...props }, ref) => {
        const Comp = asChild ? Slot : "button";
        return (
            <Comp
                className={cn(buttonVariants({ variant, size, className }))}
                ref={ref}
                {...props}
            />
        );
    },
);
Button.displayName = "Button";

export { Button, buttonVariants };
