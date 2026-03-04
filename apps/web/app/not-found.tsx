import Link from 'next/link';

export default function NotFound() {
    return (
        <div className="min-h-screen flex flex-col items-center justify-center gap-6 bg-coconut-cream px-4 text-center">
            <p className="text-7xl">🎤</p>
            <h1 className="text-5xl font-bold text-shark">404</h1>
            <h2 className="text-2xl font-semibold text-gray-700">
                This page doesn&apos;t exist
            </h2>
            <p className="text-gray-500 max-w-md">
                The page you&apos;re looking for doesn&apos;t exist or may have moved.
            </p>
            <Link href="/" className="btn btn-primary">
                Go home
            </Link>
        </div>
    );
}
