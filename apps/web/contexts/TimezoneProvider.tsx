// app/components/TimezoneProvider.tsx
"use client";

import { createContext, useContext, useState, useEffect } from "react";

const TimezoneContext = createContext({ timezone: "UTC" });

export function TimezoneProvider({ children }) {
    const [timezone, setTimezone] = useState("UTC");

    useEffect(() => {
        // This runs only on client
        setTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone);
    }, []);

    return (
        <TimezoneContext.Provider value={{ timezone }}>
            {children}
        </TimezoneContext.Provider>
    );
}

export const useTimezone = () => useContext(TimezoneContext);
