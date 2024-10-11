import { JSON_KEYS } from "../../../common/constants/keys.js";
import { db } from '../../../database/index.js';
import { readFile } from "../../../common/util/storageUtil.js";
import { UserInterface } from "../../../common/models/interfaces/user.interface.js";
import { toUser } from "../../../common/util/domainModels/user/mapper.js";

const getAdminList = async (): Promise<string[]> => {
  return readFile(process.env.USERS_FILE_NAME as string)
      .then((json: any) => {
          return json[JSON_KEYS.admins].map((object: any) => {
              return object[JSON_KEYS.email]
          })
      })
}

export const checkIfUserExists = async (email: string) => {
  return db.users.checkForExistence(email);
}

export const register = async (emailString: string, passwordHash: string) => {
  const adminList = await getAdminList();
  return db.users.add({
    email: emailString,
    password: passwordHash,
    role: adminList.includes(emailString) ? 'admin' : 'user'
  });

};

export const getUserByEmail = async (email: string): Promise<UserInterface | null> => {
  return db.users.findByEmail(email).then((user: any | null) => {
    return user ? toUser(user) : null
  })
};

export const getUserById = async (userId: number): Promise<UserInterface | null> => {
  return db.users.findById(userId).then((user: any | null) => {
    return user ? toUser(user) : null
  })
};
