// Client
export interface UserInterface {
    id: string;
    email: string;
    password?: string;
    role: string;
    zipCode?: string
    emailOptin?: boolean
}

// DB
export interface UserDTO {
    id?: number;
    email: string;
    password?: string;
    role: string;
    zip_code?: string
}
