"use client";

import { useState } from "react";

import { UserInterface } from "../../objects/interface";
import { SideDrawer } from "../sidedrawer";
import { Header } from "../header";

interface NavbarProps {
    currentUser?: UserInterface | null;
}

const Navbar: React.FC<NavbarProps> = ({ currentUser }) => {
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    return (
        <div className="fixed top-0 z-10 w-full">
            <Header currentUser={currentUser} onClick={setMobileMenuOpen} />
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
