"use client";

import Modal from "../..";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useScrapeMenuModal } from "../../../../hooks";
import axios from "axios";
import toast from "react-hot-toast";
import ScrapeClubSelectionMenuForm from "./form";
import { z } from "zod";
import { scrapeClubSelectionMenuSchema } from "./form/schema";
import { zodResolver } from "@hookform/resolvers/zod";

interface ScrapeClubSelectionMenuModalProps {
    cities: string[];
}

const ScrapeClubSelectionMenuModal: React.FC<
    ScrapeClubSelectionMenuModalProps
> = ({ cities }) => {
    const scrapeMenuModal = useScrapeMenuModal();
    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof scrapeClubSelectionMenuSchema>>({
        resolver: zodResolver(scrapeClubSelectionMenuSchema),
        defaultValues: {
            clubIds: [],
            headless: true,
        },
    });

    const onSubmit = (data: z.infer<typeof scrapeClubSelectionMenuSchema>) => {
        setIsLoading(true);
        axios
            .post("/api/scrape", {
                ids: data.clubIds,
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
            title="Select Clubs To Scrape"
            actionLabel="Continue"
            onClose={scrapeMenuModal.onClose}
            onSubmit={form.handleSubmit(onSubmit)}
            body={
                <ScrapeClubSelectionMenuForm
                    cities={cities}
                    handleLoadingState={setIsLoading}
                    form={form}
                />
            }
        />
    );
};

export default ScrapeClubSelectionMenuModal;
