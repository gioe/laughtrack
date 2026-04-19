"use client";

export function Copyright() {
    return (
        <footer
            className="px-8 py-4 text-gray-500 text-body font-dmSans"
            suppressHydrationWarning
        >
            Copyright © {new Date().getFullYear()} Laughtrack Digital, LLC
        </footer>
    );
}
