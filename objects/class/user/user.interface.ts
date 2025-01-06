// Client
export interface UserInterface {
    id: number;
    email: string;
    password?: string;
    role: string;
    zipCode: string
}

// DB
export interface UserDTO {
    id: number;
    email: string;
    password?: string;
    role: string;
    zip_code: string
}
