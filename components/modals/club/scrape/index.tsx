"use client";

import { useState } from "react";
import toast from "react-hot-toast";
import axios from "axios";
import { useRouter } from "next/navigation";
import ScrapeEntityForm from "./form";
import { z } from "zod";
import { scrapeClubSchema } from "./form/schema";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRunScrapeModal } from "../../../../hooks";
import Modal from "../..";
import EntityType from "../../../icons/MiniEntityIcon";

interface ScrapeEntityModalProps {
    entityId: number;
    type: EntityType;
}

const ScrapeEntityModal: React.FC<ScrapeEntityModalProps> = ({
    entityId,
    type,
}) => {
    const runScrapeModal = useRunScrapeModal();
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof scrapeClubSchema>>({
        resolver: zodResolver(scrapeClubSchema),
        defaultValues: {
            entityId,
            headless: "false",
        },
    });

    const onSubmit = (data: z.infer<typeof scrapeClubSchema>) => {
        setIsLoading(true);
        axios
            .post(`/api/${type.valueOf()}/${data.entityId}/scrape`, {
                headless: data.headless == "false" ? false : true,
            })
            .then((response) => {
                if (response) {
                    setIsLoading(false);
                    toast.success("Started scraping");
                    router.refresh();
                    runScrapeModal.onClose();
                }
            })
            .catch((error: Error) => {
                setIsLoading(false);
                toast.error(`${error.message}`);
            })
            .finally(() => {
                router.refresh();
            });
    };

    return (
        <Modal
            form={form}
            disabled={isLoading}
            isOpen={runScrapeModal.isOpen}
            title="Scrape"
            actionLabel="Continue"
            onClose={runScrapeModal.onClose}
            onSubmit={form.handleSubmit(onSubmit)}
            body={<ScrapeEntityForm form={form} />}
        />
    );
};

export default ScrapeEntityModal;
