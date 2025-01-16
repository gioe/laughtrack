'use server';

import { NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import { User } from "@prisma/client";
import { db } from "@/lib/db";
import { registerSchema } from "@/ui/components/form/register/schema";

export async function POST(request: Request) {

    const data = await request.json();
    const { email, password, zipCode } = await registerSchema.parseAsync(data);
    console.log(email)
    console.log(password)
    console.log(zipCode)

    const user = await db.user.findUnique(({
        where: { email: email }
    }))

    if (user && email !== "" && password !== "") {
        return NextResponse.json({
            messsage: "The user already exists"
        }, { status: 401 })
    }

    return bcrypt.hash(password, 10)
        .then((hash: string) => {
            return db.user.create({
                data: {
                    email,
                    password: hash,
                    zipCode,
                    role: 'admin'
                }
            });
        })
        .then((user: User) => {
            if (user) {
                return NextResponse.json({
                    id: user.id
                }, { status: 200 })
            }
            throw new Error("Error creating user")
        })
        .catch((error: Error) => {
            console.log(`This is the registration error: ${error}`)
            return NextResponse.json({
                error
            }, { status: 500 })
        })
}
