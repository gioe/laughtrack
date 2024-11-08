'use server';

import { NextRequest, NextResponse } from "next/server";
import { getDB } from '../../../../database'

const { db } = getDB();

export async function POST(request: NextRequest) {

    const data = await request.json();
    const { city } = data
    const clubs = await db.clubs.getAllInCity(city)
    return NextResponse.json({
        clubs
    }, { status: 200 })
}
