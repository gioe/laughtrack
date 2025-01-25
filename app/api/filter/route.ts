import { getFilters } from "@/lib/data/filters/getFilters";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
    try {
        const value = new URL(request.url).searchParams.get('entity') ?? undefined
        const filters = await getFilters(value);
        return NextResponse.json({ filters }, { status: 200 });
    } catch (error) {
        return NextResponse.json(
            { message: error instanceof Error ? error.message : 'Unknown error occurred' },
            { status: 500 }
        );
    }
}
