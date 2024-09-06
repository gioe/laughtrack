import { checkForExistence, getFirstWithCondition, upsert } from "../../util/queryUtil.js"
import { DATABASE } from "../../constants/database.js"
import { GetUserDetailsOutput, RegisterUserDTO, RegisterUserOutput } from "../../api/dto/user.dto.js";

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

