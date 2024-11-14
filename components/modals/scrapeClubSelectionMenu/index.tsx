"use client";

import Modal from "..";
import { useScrapeMenuModal } from "../../../hooks";
import { EntityType } from "../../../objects/enum";
import ScrapeEntitySelectionMenuForm from "../../form/forms/scrapeEntities";
import { useRouter } from "next/navigation";

interface ScrapeClubSelectionMenuModalProps {
    cities: string[];
}

const ScrapeClubSelectionMenuModal: React.FC<
    ScrapeClubSelectionMenuModalProps
> = ({ cities }) => {
    const scrapeMenuModal = useScrapeMenuModal();
    const router = useRouter();

    const onSubmit = () => {
        router.refresh();
        scrapeMenuModal.onClose();
    };

    const cityInputs = cities.map((city) => {
        return {
            id: city,
            name: city,
        };
    });

    return (
        <Modal
            isOpen={scrapeMenuModal.isOpen}
            onClose={scrapeMenuModal.onClose}
            body={
                <ScrapeEntitySelectionMenuForm
                    cities={cityInputs}
                    type={EntityType.Club}
                    onSubmit={onSubmit}
                />
            }
        />
    );
};

export default ScrapeClubSelectionMenuModal;
