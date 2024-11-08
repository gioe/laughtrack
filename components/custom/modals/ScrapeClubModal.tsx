"use client";

import { useState } from "react";
import Modal from "./Modal";
import Heading from "../Heading";
import toast from "react-hot-toast";
import axios from "axios";
import { useRouter } from "next/navigation";
import useRunScrapeModal from "../../../hooks/useRunScrapeModal";
import { Club } from "../../../objects/classes/club/Club";

interface ScrapeClubModalParams {
    clubString: string;
}

const ScrapeClubModal: React.FC<ScrapeClubModalParams> = ({ clubString }) => {
    const club = JSON.parse(clubString) as Club;
    const runScrapeModal = useRunScrapeModal();
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = () => {
        setIsLoading(true);
        axios
            .post("/api/scrape", {
                id: club.id,
            })
            .then((response) => {
                if (response) {
                    setIsLoading(false);
                    toast.success("Started scraping");
                    router.refresh();
                    runScrapeModal.onClose();
                }
            });
    };

    const bodyContent = (
        <div className="flex flex-col gap-4">
            <Heading title="Scrape Club" />
        </div>
    );

    return (
        <Modal
            form={}
            disabled={isLoading}
            isOpen={runScrapeModal.isOpen}
            title="Scrape"
            actionLabel="Continue"
            onClose={runScrapeModal.onClose}
            onSubmit={handleSubmit}
            body={bodyContent}
        />
    );
};

export default ScrapeClubModal;
