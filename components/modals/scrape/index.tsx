"use client";
import { useRouter } from "next/navigation";
import { useRunScrapeModal } from "../../../hooks/modalState";
import Modal from "..";
import ScrapeEntityForm from "../../form/forms/scrape";

const ScrapeEntityModal = () => {
    const runScrapeModal = useRunScrapeModal();
    const router = useRouter();

    const onSubmit = () => {
        router.refresh();
        runScrapeModal.onClose();
    };

    return (
        <Modal
            isOpen={runScrapeModal.isOpen}
            onClose={runScrapeModal.onClose}
            body={<ScrapeEntityForm entityId={entityId} onSubmit={onSubmit} />}
        />
    );
};

export default ScrapeEntityModal;
