import * as userDal from "../../../database/dal/user.js"
import { GetUserDetailsOutput, RegisterUserDTO } from "../../dto/user.dto.js";
 
export const checkIfUserExists = async (email: string) => {
  return userDal.checkIfUserExists(email)
}

export const register = async (emailString: string, passwordHash: string) => {
  return userDal.getAdminList()
  .then((adminUsers: string[]) => {
    return userDal.register({
      email: emailString,
      password: passwordHash,
      role: adminUsers.includes(emailString) ? 'admin' : 'user'
    });
  })
};

export const getUserByEmail = async (email: string): Promise<GetUserDetailsOutput> => {
  return userDal.getUserByEmail(email);
};

export const getUserById = async (userId: number) => {
  return userDal.getUserById(userId);
};
