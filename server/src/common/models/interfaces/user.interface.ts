// Client
export interface UserInterface {
  id?: number;
  email: string;
  password?: string;
  role?: string;
}

// Data
export interface CreateUserDTO {
  email: string;
  password: string;
  role: string;
}