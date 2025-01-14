"use client";

import { useState } from "react";
import { SideDrawer } from "../sidedrawer";
import { UserInterface } from "@/objects/class/user/user.interface";
import { Header } from "../header";

interface NavbarProps {
    currentUser?: UserInterface | null;
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
