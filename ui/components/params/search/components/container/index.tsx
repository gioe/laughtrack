import { StyleContextKey } from "@/objects/enum";

interface SearchBarContainerProps {
    children: React.ReactNode;
    maxWidth?: string;
    variant?: StyleContextKey;
    sizeFlip?: string;
}

export default function SearchBarContainer({
    children,
    variant = StyleContextKey.Search,
    maxWidth = "max-w-7xl",
    sizeFlip = "lg",
}: SearchBarContainerProps) {
    if (variant == StyleContextKey.Search) {
        return (
            <div
                className={`flex flex-col gap-4 rounded-lg
                bg-ivory border border-black
                px-4 py-3 shadow-lg ${maxWidth} w-full
                ${sizeFlip}:flex-row ${sizeFlip}:rounded-full ${sizeFlip}:items-center`}
            >
                {children}
            </div>
        );
    }
    return (
        <div
            className={`flex flex-col gap-4 px-4 py-3 rounded-lg gap-y-4
                    bg-coconut-cream/20 backdrop-blur
                    lg:flex-row lg:rounded-full lg:items-center`}
        >
            {children}
        </div>
    );
}
