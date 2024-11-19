"use client";

import Modal from "..";
import { useScrapeMenuModal } from "../../../hooks/modalState";
import ScrapeEntitySelectionMenuForm from "../../form/forms/scrapeEntities";
import { EntityType } from "../../../objects/enum";
import { useRouter } from "next/navigation";

interface ScrapeEntitySelectionMenuModalProps {
    type: EntityType;
    citiesString: string;
}

const ScrapeEntitySelectionMenuModal: React.FC<
    ScrapeEntitySelectionMenuModalProps
> = ({ citiesString, type }) => {
    const scrapeMenuModal = useScrapeMenuModal();
    const router = useRouter();
    const cities = JSON.parse(citiesString);

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
                    cities={cities}
                    type={type}
                    onSubmit={onSubmit}
                />
            }
        />
    );
};

export default ScrapeEntitySelectionMenuModal;
