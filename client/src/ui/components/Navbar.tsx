import { Sidebar } from './Sidebar'
import { UserButton } from '@clerk/nextjs'

export interface INavbarProps {}

export const Navbar = () => {
  return (
    <nav className="sticky top-0 w-full h-12 border-2 border-white border-y bg-white/40 backdrop-blur backdrop-filter">
    </nav>
  )
}