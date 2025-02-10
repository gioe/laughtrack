"use client";

import { createContext, useContext, ReactNode } from "react";

const ParamsContext = createContext<URLSearchParams | undefined>(undefined);

interface ParamsProviderProps {
    children: ReactNode;
    value: URLSearchParams;
}

export function ParamsProvider({ children, value }: ParamsProviderProps) {
    return (
        <ParamsContext.Provider value={value}>
            {children}
        </ParamsContext.Provider>
    );
}

export function useParams() {
    const context = useContext(ParamsContext);
    if (context === undefined) {
        throw new Error("useParams must be used within a ParamsProvider");
    }
    return context;
}
