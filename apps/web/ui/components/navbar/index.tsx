"use client";

import { Header } from "../header";
import { UserProfileInterface } from "@/app/api/profile/[id]/interface";

interface NavbarProps {
    currentUser?: UserProfileInterface | null;
}

const Navbar: React.FC<NavbarProps> = ({ currentUser }) => {
    return <Header currentUser={currentUser} />;
};

export default Navbar;
