import NextAuth from "next-auth"

declare module "next-auth" {
  /**
   * Returned by `useSession`, `getSession` and received as a prop on the `SessionProvider` React Context
   */
  interface Session {
    user: any,
    accessToken?: string,
  }

  interface User {
    accessToken?: string,
    refreshToken?: string
  }
}

import { JWT } from "next-auth/jwt"

declare module "next-auth/jwt" {
  /** Returned by the `jwt` callback and `getToken`, when using JWT sessions */
  interface JWT {
    accessToken?: string,
    refreshToken?: string,
    accessTokenExp: number
  }
}