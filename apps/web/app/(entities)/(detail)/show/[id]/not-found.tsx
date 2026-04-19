import Link from "next/link";
import { Button } from "@/ui/components/ui/button";

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
            <Button asChild variant="roundedShimmer">
                <Link href="/show/search">Browse shows</Link>
            </Button>
        </div>
    );
}
