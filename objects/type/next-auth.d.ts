


// eslint-disable-next-line @typescript-eslint/no-unused-vars
import NextAuth from "next-auth"

declare module "next-auth" {
    /**
     * Returned by `useSession`, `getSession` and received as a prop on the `SessionProvider` React Context
     */
    interface Session {
        user: {
          id: string  // Add the id field
          email: string
          name: string
          role: string
          // ... other default fields
        }
      }
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { JWT } from "next-auth/jwt"

declare module "next-auth/jwt" {
    /** Returned by the `jwt` callback and `getToken`, when using JWT sessions */
    interface JWT {
        accessToken?: string,
        refreshToken?: string,
        accessTokenExp: number
    }
}
