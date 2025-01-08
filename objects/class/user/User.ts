import { UserDTO, UserInterface } from "./user.interface";

export class User implements UserInterface {
    id: number;
    email: string;
    password?: string;
    role: string;
    zipCode: string

    constructor(input: UserDTO) {
        this.id = input.id ?? 0
        this.email = input.email
        this.role = input.role
        this.zipCode = input.zip_code ?? ""
    }

}
