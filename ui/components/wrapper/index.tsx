interface ContentWrapperProps {
    children: React.ReactNode;
}

export default function ContentWrapper({ children }: ContentWrapperProps) {
    return (
        <div className="relative h-full z-10">
            <div className="max-w-7xl mx-auto h-full">{children}</div>
        </div>
    );
}
