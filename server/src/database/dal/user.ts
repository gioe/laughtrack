import { checkForExistence, getFirstWithCondition, upsertAndReplace } from "../util/queryUtil.js"
import { DATABASE } from "../constants/database.js"
import { GetUserDetailsOutput, RegisterUserDTO, RegisterUserOutput } from "../../api/dto/user.dto.js";
import { readFile } from "../../api/util/storageUtil.js";
import { JSON_KEYS } from "../../common/constants/keys.js";
import { toUser } from "../../api/controllers/user/mapper.js";
import { UserInterface } from "../../common/interfaces/user.interface.js";

export const getAdminList = async (): Promise<string[]> => {
    return readFile(process.env.USERS_FILE_NAME as string)
        .then((json: any) => {
            return json[JSON_KEYS.admins].map((object: any) => {
                return object[JSON_KEYS.email]
            })
        })
}

export const checkIfUserExists = async (email: string): Promise<boolean> => {
    return checkForExistence(DATABASE.USERS_TABLE, "email=$1", [email])
}

export const register = async (payload: RegisterUserDTO): Promise<RegisterUserOutput> => {
    return upsertAndReplace(DATABASE.USERS_TABLE,
        `(email, password, role) VALUES($1, $2, $3)`,
        `(email)`,
        `password=$2, role=$3`,
        [payload.email, payload.password, payload.role])
};

export const getUserById = async (id: number): Promise<UserInterface> => {
    return getFirstWithCondition<GetUserDetailsOutput>(DATABASE.USERS_TABLE, `id=$1`, [id])
    .then((response: GetUserDetailsOutput) => toUser(response))
};

export const getUserByEmail = async (email: string): Promise<UserInterface> => {
    return getFirstWithCondition<GetUserDetailsOutput>(DATABASE.USERS_TABLE, `email=$1`, [email])
    .then((response: GetUserDetailsOutput) => toUser(response))

};

