export type RegisterUserDTO = {
  email: string;
  password: string;
  role: string;
}

export type RegisterUserOutput = {
  id: number;
}

export type LoginUserDTO = RegisterUserDTO;
export type LoginUserOutput = RegisterUserOutput;

export type GetUserDetailsOutput = {
  id: number;
  email: string;
  password: string;
  role: string;
}