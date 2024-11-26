"use client";

import Modal from "..";
import { useScrapeMenuModal } from "../../../hooks/modalState";
import ScrapeEntitySelectionMenuForm from "../../form/forms/scrapeIds";
import { useRouter } from "next/navigation";

const ScrapeEntitySelectionMenuModal = () => {
    const scrapeMenuModal = useScrapeMenuModal();
    const router = useRouter();
    const onSubmit = () => {
        router.refresh();
        scrapeMenuModal.onClose();
    };

    return (
        <Modal
            isOpen={scrapeMenuModal.isOpen}
            onClose={scrapeMenuModal.onClose}
            body={<ScrapeEntitySelectionMenuForm onSubmit={onSubmit} />}
        />
    );
};

export default ScrapeEntitySelectionMenuModal;
