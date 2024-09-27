export type RegisterUserDTO = {
  email: string;
  password: string;
  role: string;
}

export type RegisterUserOutput = {
  id: number;
}

export type GetUserDetailsOutput = {
  id: number;
  email: string;
  password: string;
  role: string;
}