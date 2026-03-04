'use client';

import Link from 'next/link';

interface ErrorPageProps {
    title: string;
    description: string;
    reset: () => void;
}

export default function ErrorPage({ title, description, reset }: ErrorPageProps) {
    return (
        <div className="min-h-screen flex flex-col items-center justify-center gap-6 bg-coconut-cream px-4 text-center">
            <h1 className="text-4xl font-bold text-gray-800">{title}</h1>
            <p className="text-gray-500 max-w-md">{description}</p>
            <div className="flex gap-4">
                <button
                    onClick={reset}
                    className="btn btn-primary"
                >
                    Try again
                </button>
                <Link href="/" className="btn btn-ghost">
                    Go home
                </Link>
            </div>
        </div>
    );
}
