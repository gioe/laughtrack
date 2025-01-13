import { User } from "@/objects/class/user/User";
import { UserInterface } from "@/objects/class/user/user.interface";


export interface ProfilePageData extends UserInterface { }
export interface ProfilePageResponse { user: User }
