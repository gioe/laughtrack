'use server';

import { NextResponse } from "next/server";
import { getDB } from '../../../database'
import bcrypt from "bcryptjs";
import { signInSchema } from "../../../util/validations";
import { UserInterface } from "../../../objects/class/user/user.interface";

const { database } = getDB();

export async function POST(request: Request) {

    const data = await request.json();
    const { email, password } = await signInSchema.parseAsync(data);

    const emailString = email as string;
    const passwordString = password as string;

    const userExists = await database.queries.userExists(emailString)

    if (userExists && emailString !== "" && passwordString !== "") {
        return NextResponse.json({
            messsage: "The user already exists"
        }, { status: 401 })
    }

    return bcrypt.hash(passwordString, 10)
        .then((hash: string) => {
            return database.actions.addUser({
                email: emailString,
                password: hash,
                role: 'admin'
            });
        })
        .then((user: UserInterface | null) => {
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
