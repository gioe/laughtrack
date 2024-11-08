'use server';

import { NextResponse } from "next/server";
import { runScrapingJob } from "../../../jobs/scrape";

export async function POST(request: Request) {

    const data = await request.json();
    const { ids, headless } = data
    return runScrapingJob(ids, headless)
        .then((message: string) => NextResponse.json({ message }, { status: 200 }))
        .catch((error: Error) => {
            console.error(error)
            return NextResponse.json({ message: error }, { status: 500 })
        })

}
