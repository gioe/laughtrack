import { checkForExistence, getFirstWithCondition, upsert } from "../../util/queryUtil.js"
import { DATABASE } from "../../constants/database.js"
import { GetUserDetailsOutput, RegisterUserDTO, RegisterUserOutput } from "../../api/dto/user.dto.js";
import { readFile } from "../../util/storageUtil.js";
import { JSON_KEYS } from '../../constants/objects.js';

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
    return upsert(DATABASE.USERS_TABLE, 
        `(email, password, role) VALUES($1, $2, $3)`,
        `(email)`,
        `password=$2, role=$3`,
        [payload.email, payload.password, payload.role])
  };

export const getUserById = async (id: number): Promise<GetUserDetailsOutput> => {
    return getFirstWithCondition<GetUserDetailsOutput>(DATABASE.USERS_TABLE, `id=$1`, [id])
};

export const getUserByEmail = async (email: string): Promise<GetUserDetailsOutput> => {
    return getFirstWithCondition<GetUserDetailsOutput>(DATABASE.USERS_TABLE, `email=$1`, [email])
};

