"use client";

import { Header } from "../header";
import { UserProfileInterface } from "@/app/api/profile/[id]/interface";

interface NavbarProps {
    currentUser?: UserProfileInterface | null;
}

const Navbar: React.FC<NavbarProps> = ({ currentUser }) => {
    return (
        <div className="w-full relative z-20">
            <Header currentUser={currentUser} />
        </div>
    );
};

export default Navbar;
