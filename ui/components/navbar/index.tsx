"use client";

import { useState } from "react";
import { SideDrawer } from "../sidedrawer";
import { Header } from "../header";
import { UserProfileInterface } from "@/app/api/profile/[id]/interface";

interface NavbarProps {
    currentUser?: UserProfileInterface | null;
}

const Navbar: React.FC<NavbarProps> = ({ currentUser }) => {
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    return (
        <div className="w-full">
            <Header currentUser={currentUser} />
            <div className="lg:hidden">
                <SideDrawer
                    open={mobileMenuOpen}
                    onClose={setMobileMenuOpen}
                    currentUser={currentUser}
                />
            </div>
        </div>
    );
};

export default Navbar;
