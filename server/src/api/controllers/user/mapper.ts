import { UserInterface } from '../../../common/interfaces/user.interface.js'
import { IUser } from '../../../database/models.js'

export const toUser = (payload: IUser): UserInterface => {
  return {
    id: payload.id,
    email: payload.email,
    role: payload.role,
    password: payload.password
  }
}
