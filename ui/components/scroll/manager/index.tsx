"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";

export function ScrollPositionManager() {
    const pathname = usePathname();

    useEffect(() => {
        // Store both scroll position and current path
        const handleBeforeUnload = () => {
            const scrollData = {
                position: window.scrollY,
                path: pathname,
            };
            sessionStorage.setItem("scrollData", JSON.stringify(scrollData));
        };

        // Check if we're returning to the same path
        const savedScrollData = sessionStorage.getItem("scrollData");
        if (savedScrollData) {
            const { position, path } = JSON.parse(savedScrollData);

            // Only restore scroll if the path matches
            if (path === pathname) {
                setTimeout(() => {
                    window.scrollTo(0, position);
                    sessionStorage.removeItem("scrollData");
                }, 100);
            } else {
                // Clear the stored data if paths don't match
                sessionStorage.removeItem("scrollData");
                window.scrollTo(0, 0);
            }
        }

        window.addEventListener("beforeunload", handleBeforeUnload);
        return () =>
            window.removeEventListener("beforeunload", handleBeforeUnload);
    }, [pathname]);

    return null;
}
