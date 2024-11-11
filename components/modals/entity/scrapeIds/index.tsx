"use client";

import Modal from "../..";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useScrapeMenuModal } from "../../../../hooks";
import axios from "axios";
import toast from "react-hot-toast";
import ScrapeEntitySelectionMenuForm from "./form";
import { z } from "zod";
import { scrapeEntitySelectionMenuSchema } from "./form/schema";
import { zodResolver } from "@hookform/resolvers/zod";
import EntityType from "../../../icons/MiniEntityIcon";
import { FormSelectable } from "../../../../objects/interfaces";

interface ScrapeEntitySelectionMenuModalProps {
    type: EntityType;
    citiesString: string;
}

const ScrapeEntitySelectionMenuModal: React.FC<
    ScrapeEntitySelectionMenuModalProps
> = ({ citiesString, type }) => {
    const scrapeMenuModal = useScrapeMenuModal();
    const [isLoading, setIsLoading] = useState(false);
    const cities = JSON.parse(citiesString) as FormSelectable[];

    const form = useForm<z.infer<typeof scrapeEntitySelectionMenuSchema>>({
        resolver: zodResolver(scrapeEntitySelectionMenuSchema),
        defaultValues: {
            entityType: type,
            ids: [],
            headless: true,
        },
    });

    const onSubmit = (
        data: z.infer<typeof scrapeEntitySelectionMenuSchema>,
    ) => {
        setIsLoading(true);
        axios
            .post(`/api/${type.valueOf()}/scrape`, {
                ids: data.ids,
                headless: data.headless,
            })
            .then((response) => response.data)
            .then((data) => {
                if (data) {
                    setIsLoading(false);
                    toast.success(data.message);
                }
            });
    };

    return (
        <Modal
            form={form}
            disabled={isLoading}
            isOpen={scrapeMenuModal.isOpen}
            title={`Select ${type.valueOf()}s to scrape`}
            actionLabel="Continue"
            onClose={scrapeMenuModal.onClose}
            onSubmit={form.handleSubmit(onSubmit)}
            body={
                <ScrapeEntitySelectionMenuForm
                    cities={cities}
                    handleLoadingState={setIsLoading}
                    form={form}
                />
            }
        />
    );
};

export default ScrapeEntitySelectionMenuModal;
