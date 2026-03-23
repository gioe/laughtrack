// ShowLocationComponent.tsx
"use client";

import { UseFormReturn } from "react-hook-form";
import React, { useCallback, useRef, useState } from "react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { MapPin, Loader2 } from "lucide-react";
import { ComponentVariant } from "@/objects/enum";
import DropdownComponent from "../dropdown";
import ZipCodeInput from "../zipcode/input";
import { allDistanceOptions } from "@/objects/enum/distanceValues";
import { DistanceData } from "@/objects/interface";
import { useLocationParams } from "../../hooks/useLocationParams";
import { useGeolocation, GeolocationError } from "@/hooks/useGeolocation";

const selectableDistances = allDistanceOptions.map(
    (distance: string, index: number) => ({
        id: index + 1,
        slug: distance,
        name: distance,
    }),
);

type ShowDistanceFormProps = {
    variant: ComponentVariant.Form;
    form: UseFormReturn<any>;
    inputId?: string;
};

type ShowDistanceStandaloneProps = {
    variant: ComponentVariant.Standalone;
    value: DistanceData;
    onDistanceSelection?: (value: string) => void;
    onZipcodeInput?: (value: string) => void;
    inputId?: string;
};

type ShowLocationComponentProps =
    | ShowDistanceFormProps
    | ShowDistanceStandaloneProps;

const ERROR_MESSAGES: Record<GeolocationError, string> = {
    denied: "Location access denied. Please enter your zip code.",
    timeout: "Location request timed out. Please enter your zip code.",
    unavailable: "Geolocation is not available in your browser.",
    no_zip: "Could not determine zip code from your location.",
};

const ShowLocationComponent = (props: ShowLocationComponentProps) => {
    const { getCurrentStyles } = useStyleContext();
    const { updateDistance, updateZipCode } = useLocationParams();
    const [showTooltip, setShowTooltip] = useState(false);
    const tooltipTimerRef = useRef<ReturnType<typeof setTimeout>>();

    const handleGeoSuccess = useCallback(
        (zip: string) => {
            if (props.variant === ComponentVariant.Standalone) {
                const handler = props.onZipcodeInput ?? updateZipCode;
                handler(zip);
            } else {
                props.form.setValue("distance.zipCode", zip, {
                    shouldDirty: true,
                    shouldTouch: true,
                });
            }
        },

        [props, updateZipCode],
    );

    const { status, error, requestLocation } = useGeolocation(handleGeoSuccess);

    const handleGeoClick = useCallback(() => {
        clearTimeout(tooltipTimerRef.current);
        setShowTooltip(false);
        requestLocation();
    }, [requestLocation]);

    // Show tooltip when error occurs, auto-hide after 4s
    React.useEffect(() => {
        if (error) {
            setShowTooltip(true);
            tooltipTimerRef.current = setTimeout(
                () => setShowTooltip(false),
                4000,
            );
        }
        return () => clearTimeout(tooltipTimerRef.current);
    }, [error]);

    const buildDropdownComponent = (props: ShowLocationComponentProps) => {
        if (props.variant === ComponentVariant.Form) {
            return (
                <DropdownComponent
                    items={selectableDistances}
                    name="distance.distance"
                    form={props.form}
                    variant={props.variant}
                />
            );
        }

        return (
            <DropdownComponent
                items={selectableDistances}
                onChange={props.onDistanceSelection ?? updateDistance}
                value={props.value?.distance ?? ""}
                variant={props.variant}
            />
        );
    };

    const buildZipCodeComponent = (props: ShowLocationComponentProps) => {
        if (props.variant === ComponentVariant.Form) {
            return (
                <ZipCodeInput
                    variant={props.variant}
                    form={props.form}
                    placeholder="Zip code"
                    disabled={false}
                    name="distance.zipCode"
                    id={props.inputId}
                />
            );
        }

        return (
            <ZipCodeInput
                variant={props.variant}
                value={props.value?.zipCode ?? ""}
                onChange={props.onZipcodeInput ?? updateZipCode}
                placeholder="Where"
                disabled={false}
                id={props.inputId}
            />
        );
    };

    const isLoading = status === "loading";
    const styles = getCurrentStyles();

    return (
        <div className="flex flex-wrap items-center gap-4 sm:gap-6 w-full">
            <div className="flex items-center min-w-[120px] max-w-[160px]">
                <MapPin
                    className={`w-5 h-5 mr-2 flex-shrink-0 ${styles.iconTextColor}`}
                />
                <div className="w-full">{buildDropdownComponent(props)}</div>
            </div>

            <span
                className={`text-sm sm:text-base font-normal px-2 ${styles.inputTextColor} whitespace-nowrap`}
            >
                miles around
            </span>

            <div className="w-full sm:w-auto flex-1 max-w-[200px] relative">
                <div className="flex items-center gap-1">
                    <div className="flex-1">{buildZipCodeComponent(props)}</div>
                    <div className="relative flex-shrink-0">
                        <button
                            type="button"
                            onClick={handleGeoClick}
                            disabled={isLoading}
                            aria-label="Use my location"
                            title="Use my location"
                            className={`p-1.5 rounded-md transition-colors ${styles.iconTextColor} hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                            {isLoading ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <MapPin className="w-4 h-4" />
                            )}
                        </button>
                        {showTooltip && error && (
                            <div className="absolute right-0 top-full mt-1 z-50 w-52 rounded-md bg-gray-800 px-3 py-2 text-xs text-white shadow-lg">
                                {ERROR_MESSAGES[error]}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ShowLocationComponent;
