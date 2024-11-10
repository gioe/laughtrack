"use client";

import { useState } from "react";
import { CheckboxFormComponent } from "../../../../formComponents/checkbox";
import axios from "axios";
import { DropdownFormComponent } from "../../../../formComponents/dropdown";
import { FormSelectable } from "../../../../../objects/interfaces";

interface ScrapeClubSelectionMenuFormProps {
    cities: string[];
    handleLoadingState: (loading: boolean) => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export default function ScrapeClubSelectionMenuForm({
    handleLoadingState,
    cities,
    form,
}: ScrapeClubSelectionMenuFormProps) {
    const [clubs, setClubs] = useState<FormSelectable[]>([]);

    const handleCitySelection = (selection: string) => {
        if (selection == "all") {
            setClubs([]);
        }
        handleLoadingState(true);
        axios
            .post("/api/club/city", {
                city: selection,
            })
            .then((response) => response.data)
            .then((data) => {
                if (data) {
                    setClubs(data.clubs);
                    handleLoadingState(false);
                }
            });
    };

    return (
        <div className="flex flex-col gap-4">
            <DropdownFormComponent
                name="headless"
                title="Headless"
                form={form}
                placeholder="Open browser window?"
                items={[]}
            />
            <DropdownFormComponent
                name="city"
                title="Cities"
                form={form}
                placeholder="Select city"
                items={[]}
            />
            <CheckboxFormComponent form={form} inputs={clubs} />
        </div>
    );
}
