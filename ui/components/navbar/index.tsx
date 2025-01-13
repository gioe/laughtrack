"use client";

import { useState } from "react";
import { SideDrawer } from "../sidedrawer";
import { UserInterface } from "@/objects/class/user/user.interface";
import { Header } from "../header";
import { styleContexts } from "../header/styles";

interface NavbarProps {
    currentUser?: UserInterface | null;
    context?: keyof typeof styleContexts;
}

const Navbar: React.FC<NavbarProps> = ({ currentUser, context = "home" }) => {
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    return (
        <div className="w-full">
            <Header currentUser={currentUser} styleContext={context} />
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
