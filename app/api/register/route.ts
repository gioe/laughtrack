import { NextResponse } from "next/server";
import bcrypt from "bcrypt";
import { UserInterface } from "../../../interfaces/user.interface.js";
import { getDB } from '../../../database'
import { JSON_KEYS } from "../../../util/constants/keys.js";
import { readFile } from "../../../util/storageUtil.js";

const { db } = getDB();

export async function POST(request: Request) {

    const data = await request.json();
    const { email, password } = data
    const emailString = email as string;
    const passwordString = password as string;

    const userExists = await db.users.checkForExistence(emailString)

    if (userExists && emailString !== "" && passwordString !== "") {
        NextResponse.json({
            messsage: "The user already exists"
        }, { status: 401 })
    }
    const adminList = await getAdminList();


    return bcrypt.hash(passwordString, 10)
        .then((hash: string) => {
            return db.users.add({
                email: emailString,
                password: hash,
                role: adminList.includes(emailString) ? 'admin' : 'user'
            });
        })
        .then((user: UserInterface | null) => {
            if (user) {
                NextResponse.json({
                    id: user.id
                }, { status: 200 })
            }
            throw new Error("Error creating user")
        })
        .catch((error: any) =>
            NextResponse.json({
                error
            }, { status: 500 })
        )
}

const getAdminList = async (): Promise<string[]> => {
    return readFile(process.env.USERS_FILE_NAME as string)
        .then((json: any) => {
            return json[JSON_KEYS.admins].map((object: any) => {
                return object[JSON_KEYS.email]
            })
        })
}
