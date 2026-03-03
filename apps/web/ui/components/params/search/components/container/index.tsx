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
        flex flex-col
        p-3 md:p-4
        rounded-2xl
        transition-all duration-200
        shadow-md hover:shadow-lg
        backdrop-blur-sm
    `;

    // Variant-specific classes
    const variantClasses =
        variant === StyleContextKey.Search
            ? "bg-ivory/95 border border-black/10"
            : "bg-coconut-cream/30 border border-white/20";

    return <div className={`${baseClasses} ${variantClasses}`}>{children}</div>;
}
