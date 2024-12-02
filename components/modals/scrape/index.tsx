"use client";
import { useRouter } from "next/navigation";
import { useRunScrapeModal } from "../../../hooks/modalState";
import Modal from "..";
import ScrapeEntityForm from "../../form/scrape";

interface ScrapeEntityModalProps {
    identifier: string;
}
const ScrapeEntityModal = ({ identifier }: ScrapeEntityModalProps) => {
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
            body={
                <ScrapeEntityForm identifier={identifier} onSubmit={onSubmit} />
            }
        />
    );
};

export default ScrapeEntityModal;
