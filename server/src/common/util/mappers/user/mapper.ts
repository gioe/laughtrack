import { UserInterface } from "../../../interfaces/client/user.interface.js"

export const toUser = (payload: any): UserInterface => {
  return {
    id: payload.id,
    email: payload.email,
    role: payload.role,
    password: payload.password
  }
}

