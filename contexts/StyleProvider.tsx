"use client";

import { StyleContextKey } from "@/objects/enum";
import React, { createContext, useContext, useState, ReactNode } from "react";

type TailwindTextColor =
    | "text-white"
    | "text-black"
    | "text-cedar"
    | "text-gray-400"
    | "text-copper";
type TailwindBgColor = "bg-copper" | "bg-black";

export interface StyleValues {
    iconTextColor: TailwindTextColor;
    logoTextColor: TailwindTextColor;
    buttonColor: TailwindBgColor;
    headerItemColorHighlighted: TailwindTextColor;
    baseHeaderItemColor: TailwindTextColor;
    baseHeaderItemHoverColor: TailwindTextColor;
    iconBgColor: TailwindBgColor;
}

export interface StyleContext {
    key: StyleContextKey;
    values: StyleValues;
}

export type StyleContexts = StyleContext[];

// Define the initial style contexts
export const styleContexts: StyleContexts = [
    {
        key: StyleContextKey.Home,
        values: {
            iconTextColor: "text-copper",
            logoTextColor: "text-white",
            buttonColor: "bg-copper",
            baseHeaderItemColor: "text-white",
            baseHeaderItemHoverColor: "text-gray-400",
            iconBgColor: "bg-copper",
        },
    },
    {
        key: StyleContextKey.Search,
        values: {
            iconTextColor: "text-copper",
            logoTextColor: "text-black",
            buttonColor: "bg-black",
            headerItemColorHighlighted: "text-cedar",
            baseHeaderItemColor: "text-cedar",
            baseHeaderItemHoverColor: "text-cedar",
            iconBgColor: "bg-copper",
        },
    },
];

interface StyleContextProviderState {
    currentContext: StyleContextKey;
    setCurrentContext: (context: StyleContextKey) => void;
    getCurrentStyles: () => StyleValues;
    getStylesForContext: (context: StyleContextKey) => StyleValues;
}

const StyleContextProviderContext = createContext<
    StyleContextProviderState | undefined
>(undefined);

interface StyleContextProviderProps {
    children: ReactNode;
    initialContext?: StyleContextKey;
}

export function StyleContextProvider({
    children,
    initialContext = StyleContextKey.Home,
}: StyleContextProviderProps) {
    const [currentContext, setCurrentContext] =
        useState<StyleContextKey>(initialContext);

    const getStylesForContext = (context: StyleContextKey): StyleValues => {
        const styles = styleContexts.find((ctx) => ctx.key === context)?.values;
        if (!styles) {
            throw new Error(`No styles found for context: ${context}`);
        }
        return styles;
    };

    const getCurrentStyles = (): StyleValues => {
        return getStylesForContext(currentContext);
    };

    const value = {
        currentContext,
        setCurrentContext,
        getCurrentStyles,
        getStylesForContext,
    };

    return (
        <StyleContextProviderContext.Provider value={value}>
            {children}
        </StyleContextProviderContext.Provider>
    );
}

// Custom hook to use the style context
export function useStyleContext() {
    const context = useContext(StyleContextProviderContext);
    if (context === undefined) {
        throw new Error(
            "useStyleContext must be used within a StyleContextProvider",
        );
    }
    return context;
}
