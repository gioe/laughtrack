import { StyleContextKey } from "@/objects/enum";

interface SearchBarContainerProps {
    children: React.ReactNode;
    maxWidth?: string;
    variant?: StyleContextKey;
}

export default function SearchBarContainer({
    children,
    variant = StyleContextKey.Search,
    maxWidth = "max-w-7xl",
}: SearchBarContainerProps) {
    if (variant == StyleContextKey.Search) {
        return (
            <div
                className={`flex flex-col rounded-lg
                bg-ivory border border-black
                px-4 py-3 shadow-lg ${maxWidth}
                lg:flex-row lg:rounded-full lg:items-center`}
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
