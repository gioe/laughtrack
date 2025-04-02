// SearchBarContainer.tsx
import { StyleContextKey } from "@/objects/enum";

interface SearchBarContainerProps {
    children: React.ReactNode;
    maxWidth?: string;
    variant?: StyleContextKey;
}

export default function SearchBarContainer({
    children,
    variant = StyleContextKey.Search,
    maxWidth = "max-w-4xl",
}: SearchBarContainerProps) {
    // Common classes for both variants
    const baseClasses = `
        w-full mx-auto ${maxWidth}
        flex flex-col gap-4
        p-4 rounded-lg
        transition-all duration-200
        md:p-4 md:gap-4
        lg:flex-row lg:items-center lg:rounded-full
    `;

    // Variant-specific classes
    const variantClasses =
        variant === StyleContextKey.Search
            ? "bg-ivory border border-black shadow-lg"
            : "bg-coconut-cream/20 backdrop-blur";

    return <div className={`${baseClasses} ${variantClasses}`}>{children}</div>;
}
