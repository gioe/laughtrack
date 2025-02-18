interface SearchBarContainerProps {
    children: React.ReactNode;
}

export default function SearchBarContainer({
    children,
}: SearchBarContainerProps) {
    return (
        <div
            className="flex items-center bg-ivory
         rounded-full border border-black
         px-4 py-3 shadow-lg max-w-7xl w-full"
        >
            {children}
        </div>
    );
}
