import Link from "next/link";

export default function ShowNotFound() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6 text-center">
            <p className="text-7xl">🎟️</p>
            <h1 className="text-5xl font-bold text-shark">404</h1>
            <h2 className="text-2xl font-semibold text-gray-700">
                This show isn&apos;t on the bill
            </h2>
            <p className="text-gray-500 max-w-md">
                We couldn&apos;t find this show — it may have been removed or
                never existed.
            </p>
            <Link
                href="/show/search"
                className="inline-flex items-center justify-center px-6 py-3 rounded-lg bg-copper text-white font-dmSans font-bold text-base shadow-sm hover:bg-copper/90 hover:shadow-md hover:-translate-y-[1px] transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
            >
                Browse shows
            </Link>
        </div>
    );
}
