

// utils/auth.ts
import { signOut } from "next-auth/react"
import { usePathname, useRouter } from "next/navigation";

// Pages that should redirect to a specific page on sign out
const PROTECTED_PAGES = [
  '/profile',
]

// Where to redirect if signing out from a protected page
const DEFAULT_SIGNOUT_REDIRECT = '/'

export const useSignOut = () => {
    const router = useRouter()
    const path = usePathname()

    const handleSignOut = async () => {
      // Get current path
      const currentPath = path

      // Check if we're on a protected page
      const shouldRedirect = PROTECTED_PAGES.some(page =>
        currentPath.startsWith(page)
      )

      if (shouldRedirect) {
        // Sign out and redirect
        await signOut({
          callbackUrl: DEFAULT_SIGNOUT_REDIRECT,
          redirect: true
        })
      } else {
        // Sign out but stay on current page
        await signOut({
          redirect: false
        })
        // Optionally refresh the page to update UI
        router.refresh()
      }
    }

    return handleSignOut
  }
