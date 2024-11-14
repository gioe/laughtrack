// Client
export interface UserInterface {
    id: number;
    email: string;
    password?: string;
    role: string;
}

// DB
export interface UserDTO {
    email: string;
    password: string;
    role: string;
}
