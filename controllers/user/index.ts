import { JSON_KEYS } from "../../util/constants/keys";
import { getDB } from "../../database/index.js";
import { readFile } from "../../util/storageUtil";
import { UserInterface } from "../../interfaces";
import { toUser } from "../../util/domainModels/user/mapper";

const { db } = getDB();

const getAdminList = async (): Promise<string[]> => {
    return readFile(process.env.USERS_FILE_NAME as string).then((json: any) => {
        return json[JSON_KEYS.admins].map((object: any) => {
            return object[JSON_KEYS.email];
        });
    });
};

export const register = async (emailString: string, passwordHash: string) => {
    const adminList = await getAdminList();

    return db.users.add({
        email: emailString,
        password: passwordHash,
        role: adminList.includes(emailString) ? "admin" : "user",
    });
};

export const getUserByEmail = async (
    email: string,
): Promise<UserInterface | null> => {
    return db.users
        .findByEmail(email)
        .then((user: any | null) => (user ? toUser(user) : null));
};

export const getUserById = async (
    userId: number,
): Promise<UserInterface | null> => {
    return db.users
        .findById(userId)
        .then((user: any | null) => (user ? toUser(user) : null));
};
