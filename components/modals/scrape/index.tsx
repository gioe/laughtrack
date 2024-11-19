"use client";
import { useRouter } from "next/navigation";
import { useRunScrapeModal } from "../../../hooks/modalState";
import Modal from "..";
import { EntityType } from "../../../objects/enum";
import ScrapeEntityForm from "../../form/forms/scrape";

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

    const onSubmit = () => {
        router.refresh();
        runScrapeModal.onClose();
    };

    return (
        <Modal
            isOpen={runScrapeModal.isOpen}
            onClose={runScrapeModal.onClose}
            body={
                <ScrapeEntityForm
                    entityId={entityId}
                    type={type}
                    onSubmit={onSubmit}
                />
            }
        />
    );
};

export default ScrapeEntityModal;
