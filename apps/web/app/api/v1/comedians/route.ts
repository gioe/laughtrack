import { NextResponse } from "next/server";
import { getTrendingComedians } from "@/lib/data/home/getTrendingComedians";

export async function GET() {
    try {
        const comedians = await getTrendingComedians();
        return NextResponse.json({ data: comedians });
    } catch (error) {
        console.error("GET /api/v1/comedians error:", error);
        return NextResponse.json({ error: "Failed to fetch comedians" }, { status: 500 });
    }
}
