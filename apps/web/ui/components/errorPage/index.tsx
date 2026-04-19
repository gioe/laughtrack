"use client";

import Link from "next/link";
import { Button } from "@/ui/components/ui/button";

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
                <Button type="button" variant="roundedShimmer" onClick={reset}>
                    Try again
                </Button>
                <Button asChild variant="roundedShimmerOutline">
                    <Link href="/">Go home</Link>
                </Button>
            </div>
        </div>
    );
}
