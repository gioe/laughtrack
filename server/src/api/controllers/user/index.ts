import * as userDal from "../../../database/dal/user.js"
import { LoginUserDTO, RegisterUserDTO, RegisterUserOutput } from "../../dto/user.dto.js";
 
export const checkIfUserExists = async (email: string) => {
  return userDal.checkIfUserExists(email)
}

export const register = async (params: RegisterUserDTO) => {
  return userDal.register(params).then((output: RegisterUserOutput) => {
    return userDal.getUserById(output.id)
  });
};

export const getUserByEmail = async (email: string) => {
  return userDal.getUserByEmail(email);
};
