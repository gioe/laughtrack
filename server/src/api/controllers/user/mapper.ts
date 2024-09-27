import { UserInterface } from '../../../common/interfaces/user.interface.js'
import { GetUserDetailsOutput } from '../../dto/user.dto.js'

export const toUser = (payload: GetUserDetailsOutput): UserInterface => {
  return {
    id: payload.id,
    email: payload.email,
    role: payload.role,
    password: payload.password
  }
}
