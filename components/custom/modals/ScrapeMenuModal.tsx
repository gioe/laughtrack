"use client";

import Modal from "./Modal";
import { useState } from "react";
import { FieldValues, SubmitHandler, useForm } from "react-hook-form";
import { useScrapeMenuModal } from "../../../hooks";
import { CheckboxComponent, CheckboxComponentItem } from "../checkbox/Checkbox";
import axios from "axios";
import toast from "react-hot-toast";
import {
    ComboBoxItemInterface,
    DropdownSelectComponent,
} from "../dropdown/DropdownSelectComponent";

interface ScrapeMenuModalProps {
    cities: string[];
}

const ScrapeMenuModal: React.FC<ScrapeMenuModalProps> = ({ cities }) => {
    const { handleSubmit } = useForm<FieldValues>();
    const [clubs, setClubs] = useState<CheckboxComponentItem[]>([]);
    const [selectedClubs, setSelectedClubs] = useState<string[]>([]);
    const [headless, setHeadless] = useState(false);

    const scrapeMenuModal = useScrapeMenuModal();

    const [isLoading, setIsLoading] = useState(false);

    const handleHeadlessSelection = (selection: string) => {
        const selectionNumber = Number(selection);
        setHeadless(selectionNumber == 1 ? true : false);
    };

    const handleCitySelection = (selection: string) => {
        if (selection == "all") {
            setClubs([]);
        }
        setIsLoading(true);
        axios
            .post("/api/club/city", {
                city: selection,
            })
            .then((response) => response.data)
            .then((data) => {
                if (data) {
                    setClubs(data.clubs);
                    setIsLoading(false);
                }
            });
    };

    const handleChange = (values: string[]) => {
        setSelectedClubs(values);
    };

    const onSubmit: SubmitHandler<FieldValues> = () => {
        console.log(headless);
        setIsLoading(true);
        axios
            .post("/api/scrape", {
                ids: selectedClubs,
                headless,
            })
            .then((response) => response.data)
            .then((data) => {
                if (data) {
                    setIsLoading(false);
                    toast.success(data.message);
                }
            });
    };

    const cityItems = cities.map((city: string) => {
        return {
            value: city,
            label: city,
        };
    }) as ComboBoxItemInterface[];

    const bodyContent = (
        <div className="flex flex-col gap-4">
            <DropdownSelectComponent
                placeholder={"Open browser window?"}
                items={[
                    {
                        value: "0",
                        label: "No",
                    },
                    {
                        value: "1",
                        label: "Yes",
                    },
                ]}
                handleSelection={handleHeadlessSelection}
            />
            <DropdownSelectComponent
                placeholder={"Select city"}
                items={[
                    {
                        value: "all",
                        label: "All",
                    },
                ].concat(cityItems)}
                handleSelection={handleCitySelection}
            />
            <CheckboxComponent
                inputs={clubs}
                handleValueChange={handleChange}
            />
        </div>
    );

    return (
        <Modal
            disabled={isLoading}
            isOpen={scrapeMenuModal.isOpen}
            title="Select Clubs To Scrape"
            actionLabel="Continue"
            onClose={scrapeMenuModal.onClose}
            onSubmit={handleSubmit(onSubmit)}
            body={bodyContent}
        />
    );
};

export default ScrapeMenuModal;
