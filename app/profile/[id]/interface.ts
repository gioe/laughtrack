/* eslint-disable @typescript-eslint/no-empty-object-type */
import { UserInterface } from "../../../objects/class/user/user.interface";
import { User } from "../../../objects/type/user";

export interface ProfilePageData extends UserInterface { }
export interface ProfilePageResponse { user: User }
