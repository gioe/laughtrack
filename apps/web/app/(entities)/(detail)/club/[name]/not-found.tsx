import Link from "next/link";

export default function ClubNotFound() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6 text-center">
            <p className="text-7xl">🏢</p>
            <h1 className="text-5xl font-bold text-shark">404</h1>
            <h2 className="text-2xl font-semibold text-gray-700">
                This venue isn&apos;t in our listings
            </h2>
            <p className="text-gray-500 max-w-md">
                We couldn&apos;t find this club — it may have closed or
                hasn&apos;t been added yet.
            </p>
            <Link
                href="/club/search"
                className="inline-flex items-center justify-center px-6 py-3 rounded-lg bg-copper text-white font-dmSans font-bold text-base shadow-sm hover:bg-copper/90 hover:shadow-md hover:-translate-y-[1px] transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
            >
                Back to search
            </Link>
        </div>
    );
}
