"use client";

import Link from "next/link";

interface ErrorPageProps {
    title: string;
    description: string;
    reset: () => void;
}

export default function ErrorPage({
    title,
    description,
    reset,
}: ErrorPageProps) {
    return (
        <div className="min-h-screen flex flex-col items-center justify-center gap-6 bg-coconut-cream px-4 text-center">
            <h1 className="text-4xl font-bold text-gray-800">{title}</h1>
            <p className="text-gray-500 max-w-md">{description}</p>
            <div className="flex gap-4">
                <button
                    onClick={reset}
                    className="inline-flex items-center justify-center px-6 py-3 rounded-lg bg-copper text-white font-dmSans font-bold text-base shadow-sm hover:bg-copper/90 hover:shadow-md hover:-translate-y-[1px] transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
                >
                    Try again
                </button>
                <Link
                    href="/"
                    className="inline-flex items-center justify-center px-6 py-3 rounded-lg border-2 border-copper text-copper font-dmSans font-bold text-base hover:bg-copper hover:text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
                >
                    Go home
                </Link>
            </div>
        </div>
    );
}
