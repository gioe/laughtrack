import { UserDTO, UserInterface } from "./user.interface";

export class User implements UserInterface {
    id: string;
    email: string;
    password?: string;
    role: string;
    zipCode: string

    constructor(input: UserDTO) {
        this.id = input.id ?? ""
        this.email = input.email
        this.role = input.role
        this.zipCode = input.zip_code ?? ""
    }

}
