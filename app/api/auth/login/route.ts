'use server';

import { NextResponse } from "next/server";
import { generateToken } from "@/util/token";
import bcrypt from "bcryptjs";
import { db } from "@/lib/db";

export async function POST(request: Request) {
    const data = await request.json();
    const { email, password } = data
    const user = await db.user.findUnique(({
        where: { email: email }
    }))

    if (!user) {
        return NextResponse.json({ error: "User doesn't exist." }, { status: 400 });
    }

    const passwordMatch = await bcrypt.compare(password, user.password ?? "")

    if (!passwordMatch) {
        return NextResponse.json({ error: "Invalid credentials" }, { status: 400 });
    }

    const accessToken = generateToken({ id: user.id, email: user.email }, 'access');
    const refreshToken = generateToken({ id: user.id, email: user.email }, 'refresh');

    return NextResponse.json({
        accessToken,
        refreshToken,
        id: user.id.toString(),
        email: user.email,
        role: user.role,
        zipCode: user.zipCode
    }, { status: 200 });

}
