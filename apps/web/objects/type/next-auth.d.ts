import { UserProfileInterface } from "@/app/api/profile/[id]/interface";

declare module "next-auth" {
    /**
     * Returned by `useSession`, `getSession` and received as a prop on the `SessionProvider` React Context
     */
    interface Session {
        profile: UserProfileInterface | null;
    }
}

declare module "next-auth/jwt" {
    /** Returned by the `jwt` callback and `getToken`, when using JWT sessions */
    interface JWT {
        accessToken?: string;
        refreshToken?: string;
        accessTokenExp: number;
    }
}
