import { UserInterface } from "../../../interfaces"

export const toUser = (payload: any): UserInterface => {
  return {
    id: payload.id,
    email: payload.email,
    role: payload.role,
    password: payload.password
  }
}

