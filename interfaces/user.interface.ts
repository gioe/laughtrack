// Client
export interface UserInterface {
    id?: number;
    email: string;
    password?: string;
    role?: string;
}

// DB
export interface CreateUserDTO {
    email: string;
    password: string;
    role: string;
}
