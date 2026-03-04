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
            title="Could not load this page"
            description="Something went wrong while loading this content. Try again or return home."
            reset={reset}
        />
    );
}
