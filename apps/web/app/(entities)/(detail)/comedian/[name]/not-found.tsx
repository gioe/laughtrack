import Link from "next/link";

export default function ComedianNotFound() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6 text-center">
            <p className="text-7xl">🎤</p>
            <h1 className="text-5xl font-bold text-shark">404</h1>
            <h2 className="text-2xl font-semibold text-gray-700">
                Looks like this act isn&apos;t in our lineup
            </h2>
            <p className="text-gray-500 max-w-md">
                We couldn&apos;t find what you&apos;re looking for — maybe
                they&apos;re between gigs.
            </p>
            <Link href="/comedian/search" className="btn btn-primary">
                Back to search
            </Link>
        </div>
    );
}
