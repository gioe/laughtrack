'use client';

import { useEffect } from 'react';
import ErrorPage from '@/ui/components/errorPage';

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
        <ErrorPage
            title="Something went wrong"
            description="An unexpected error occurred. You can try again or head back to the home page."
            reset={reset}
        />
    );
}
