"use client";

import { useRouter } from "next/navigation";
import { TagInterface } from "../../../objects/interface/tag.interface";
import Modal from "..";
import TagEntityForm from "../../form/forms/tagEntity";
import { EntityType } from "../../../objects/enum";
import useAddEntityTagModal from "../../../hooks/useAddEntityTagModal";

interface TagEntityModalProps {
    type: EntityType;
    entityId: number;
    tagsString: string;
}

const TagEntityModal: React.FC<TagEntityModalProps> = ({
    type,
    entityId,
    tagsString,
}) => {
    // const tags = JSON.parse(tagsString) as TagInterface[];
    const tags = [];

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
                    tags={tags}
                    entityId={entityId}
                    type={type}
                    onSubmit={onSubmit}
                />
            }
        />
    );
};

export default TagEntityModal;
