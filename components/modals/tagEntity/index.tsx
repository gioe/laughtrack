"use client";

import { useRouter } from "next/navigation";
import Modal from "..";
import TagEntityForm from "../../form/forms/tagEntity";
import { EntityType } from "../../../objects/enum";
import useAddEntityTagModal from "../../../hooks/modalState/useAddEntityTagModal";
import { useFilterContext } from "../../../contexts/FilterContext";
import { FilterContainer } from "../../../objects/class/tag/FilterContainer";

interface TagEntityModalProps {
    type: EntityType;
    entityId: number;
}

const TagEntityModal: React.FC<TagEntityModalProps> = ({ type, entityId }) => {
    const { filters } = useFilterContext();
    const containers = filters.filter(
        (container: FilterContainer) => container.type == EntityType.Comedian,
    );

    const router = useRouter();
    const addEntityTagModal = useAddEntityTagModal();

    const onSubmit = () => {
        router.refresh();
        addEntityTagModal.onClose();
    };

    return (
        <Modal
            isOpen={addEntityTagModal.isOpen}
            onClose={addEntityTagModal.onClose}
            body={
                <TagEntityForm
                    containers={containers}
                    entityId={entityId}
                    type={type}
                    onSubmit={onSubmit}
                />
            }
        />
    );
};

export default TagEntityModal;
