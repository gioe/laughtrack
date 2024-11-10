"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import { TagInterface } from "../../../objects/interfaces/tag.interface";
import useAddShowTagModal from "../../../hooks/useAddEntityTagModal";
import axios from "axios";
import Modal from "..";
import toast from "react-hot-toast";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { tagEntitySchema } from "./form/schema";
import TagEntityForm from "./form";
import EntityType from "../../icons/MiniEntityIcon";

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
    const tags = JSON.parse(tagsString) as TagInterface[];

    const router = useRouter();
    const addShowTagModal = useAddShowTagModal();

    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof tagEntitySchema>>({
        resolver: zodResolver(tagEntitySchema),
        defaultValues: {
            entityId,
            tagIds: [],
        },
    });

    const onSubmit = (data: z.infer<typeof tagEntitySchema>) => {
        setIsLoading(true);

        axios
            .post(`/api/${type.valueOf()}/${data.entityId}/addTag`, {
                tags: data.tagIds,
            })
            .then((response) => {
                if (response) {
                    setIsLoading(false);
                    toast.success("Successfully updated");
                    router.refresh();
                    addShowTagModal.onClose();
                }
            });
    };

    return (
        <Modal
            form={form}
            disabled={isLoading}
            isOpen={addShowTagModal.isOpen}
            title="Add Tags"
            actionLabel="Continue"
            onClose={addShowTagModal.onClose}
            onSubmit={form.handleSubmit(onSubmit)}
            body={<TagEntityForm tags={tags} form={form} />}
        />
    );
};

export default TagEntityModal;
