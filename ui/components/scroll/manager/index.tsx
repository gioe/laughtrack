// components/ScrollPositionManager.tsx
"use client";

import { useEffect } from "react";

export function ScrollPositionManager() {
    useEffect(() => {
        const savedScrollPosition = sessionStorage.getItem("scrollPosition");
        if (savedScrollPosition) {
            setTimeout(() => {
                window.scrollTo(0, parseInt(savedScrollPosition));
                sessionStorage.removeItem("scrollPosition");
            }, 100);
        }

        const handleBeforeUnload = () => {
            sessionStorage.setItem("scrollPosition", window.scrollY.toString());
        };

        window.addEventListener("beforeunload", handleBeforeUnload);
        return () =>
            window.removeEventListener("beforeunload", handleBeforeUnload);
    }, []);

    return null;
}
