"use client";

import Modal from "..";
import { useScrapeMenuModal } from "../../../hooks/modalState";
import ScrapeEntitySelectionMenuForm from "../../form/forms/scrapeIds";
import { EntityType } from "../../../objects/enum";
import { useRouter } from "next/navigation";

interface ScrapeEntitySelectionMenuModalProps {
    type: EntityType;
}

const ScrapeEntitySelectionMenuModal: React.FC<
    ScrapeEntitySelectionMenuModalProps
> = ({ type }) => {
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
            body={
                <ScrapeEntitySelectionMenuForm
                    type={type}
                    onSubmit={onSubmit}
                />
            }
        />
    );
};

export default ScrapeEntitySelectionMenuModal;
