"use client";

import Modal from "..";
import { useScrapeMenuModal } from "../../../hooks/modalState";
import ScrapeEntitySelectionMenuForm from "../../form/forms/scrapeIds";
import { EntityType } from "../../../objects/enum";
import { useRouter } from "next/navigation";
import { City } from "../../../objects/class/city/City";

interface ScrapeEntitySelectionMenuModalProps {
    type: EntityType;
    citiesString: string;
}

const ScrapeEntitySelectionMenuModal: React.FC<
    ScrapeEntitySelectionMenuModalProps
> = ({ citiesString, type }) => {
    const scrapeMenuModal = useScrapeMenuModal();
    const router = useRouter();
    const cities = JSON.parse(citiesString) as City[];

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
