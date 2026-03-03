// app/components/ClientTimezone.tsx
"use client";

import { useEffect } from "react";
import { useTimezone } from "./TimezoneProvider";

export function ClientTimezone() {
    const { timezone } = useTimezone();

    useEffect(() => {
        // Set timezone cookie on client
        document.cookie = `timezone=${timezone};path=/;max-age=${30 * 24 * 60 * 60}`;
    }, [timezone]);

    return null;
}
