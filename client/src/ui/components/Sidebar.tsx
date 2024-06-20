'use client'
import { Menu, Lock, LucideIcon, User, ScreenShare } from 'lucide-react'

import Link from 'next/link'
import { SignOutButton } from '@clerk/nextjs'


import { useAuth } from '@clerk/nextjs'

export interface INavSidebarProps {}

const menu: { href: string; title: string; icon: LucideIcon }[] = [
  { href: '/user', title: 'user', icon: User },
  { href: '/admin', title: 'admin', icon: Lock },
  { href: '/manager', title: 'manager', icon: ScreenShare },
]

export function Sidebar() {
  const user = useAuth()

  if (!user.isSignedIn) {
    return (
      <>
      </>
    )
  }
  return (
    <></>
  )
}