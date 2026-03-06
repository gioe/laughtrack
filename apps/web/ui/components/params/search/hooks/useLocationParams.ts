import { useCallback, useEffect, useRef } from "react";
import { useUrlParams } from "@/hooks/useUrlParams";
import { QueryProperty } from "@/objects/enum";
import { DistanceData } from "@/objects/interface";

export function useLocationParams() {
    const { getTypedParam, setTypedParam } = useUrlParams();
    const zipTimerRef = useRef<ReturnType<typeof setTimeout>>();

    useEffect(() => () => clearTimeout(zipTimerRef.current), []);

    const getLocationState = useCallback(
        (): DistanceData => ({
            distance: getTypedParam(QueryProperty.Distance),
            zipCode: getTypedParam(QueryProperty.Zip),
        }),
        [getTypedParam],
    );

    // Debounced zip code update to prevent too many URL changes while typing
    const updateZipCode = useCallback(
        (value: string) => {
            clearTimeout(zipTimerRef.current);
            zipTimerRef.current = setTimeout(() => {
                setTypedParam(QueryProperty.Zip, value);
            }, 500);
        },
        [setTypedParam],
    );

    // Immediate distance update since it's a dropdown selection
    const updateDistance = useCallback(
        (value: string) => {
            setTypedParam(QueryProperty.Distance, value);
        },
        [setTypedParam],
    );

    return {
        getLocationState,
        updateZipCode,
        updateDistance,
    };
}
