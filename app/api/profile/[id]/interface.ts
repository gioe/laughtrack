import { UserInterface } from "@/objects/class/user/user.interface";

export interface UserProfileResponse {
    zipCode: string | null
    emailOptin?: boolean
    email: string,
    id: string
}
