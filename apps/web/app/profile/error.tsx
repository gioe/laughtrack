'use client';

import { useEffect } from 'react';
import Link from 'next/link';

export default function Error({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error(error, { digest: error.digest });
    }, [error]);

    return (
        <div className="min-h-screen flex flex-col items-center justify-center gap-6 bg-coconut-cream px-4 text-center">
            <h1 className="text-4xl font-bold text-gray-800">Could not load profile</h1>
            <p className="text-gray-500 max-w-md">
                Something went wrong while loading this profile. Try again or return home.
            </p>
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
