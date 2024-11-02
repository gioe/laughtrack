"use client";

import { useState } from "react";
import { FieldValues, SubmitHandler, useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import { ComedianInterface } from "../../../interfaces";
import useSocialDataModal from "../../../hooks/useSocialDataModal";
import Modal from "./Modal";
import Heading from "../Heading";
import StylizedInput from "../inputs/StylizedInput";
import toast from "react-hot-toast";
import axios from "axios";

interface EditSocialDataModalProps {
    comedian: ComedianInterface;
}

const EditSocialDataModal: React.FC<EditSocialDataModalProps> = ({
    comedian,
}) => {
    const socialDataModal = useSocialDataModal();
    const router = useRouter();

    const [isLoading, setIsLoading] = useState(false);

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<FieldValues>({
        defaultValues: {
            instagramAccount: comedian?.socialData?.instagramAccount ?? "",
            instagramFollowers: comedian?.socialData?.instagramFollowers ?? "",
            tiktokAccount: comedian?.socialData?.tiktokAccount ?? "",
            tiktokFollowers: comedian?.socialData?.tiktokFollowers ?? "",
            youtubeAccount: comedian?.socialData?.youtubeAccount ?? "",
            youtubeFollowers: comedian?.socialData?.youtubeFollowers ?? "",
            website: comedian?.socialData?.website ?? "",
        },
    });

    const onSubmit: SubmitHandler<FieldValues> = (data) => {
        setIsLoading(true);

        axios
            .post("/api/editSocial", {
                ...data,
                id: comedian?.id,
            })
            .then((response) => {
                if (response) {
                    setIsLoading(false);
                    toast.success("Successfully updated");
                    router.refresh();
                    socialDataModal.onClose();
                }
            });
    };

    const bodyContent = (
        <div className="flex flex-col gap-4">
            <Heading title="Edit" subtitle="Update comedian social data" />
            <StylizedInput
                id="instagramAccount"
                label="Instagram Account"
                disabled={isLoading}
                register={register}
                errors={errors}
            />
            <StylizedInput
                id="instagramFollowers"
                label="Instagram Followers"
                disabled={isLoading}
                register={register}
                errors={errors}
            />
            <StylizedInput
                id="tiktokAccount"
                label="TikTok Account"
                disabled={isLoading}
                register={register}
                errors={errors}
            />
            <StylizedInput
                id="tiktokFollowers"
                label="TikTok Followers"
                disabled={isLoading}
                register={register}
                errors={errors}
            />
            <StylizedInput
                id="youtubeAccount"
                label="Youtube Account"
                disabled={isLoading}
                register={register}
                errors={errors}
            />
            <StylizedInput
                id="youtubeFollowers"
                label="YouTube Followers"
                disabled={isLoading}
                register={register}
                errors={errors}
            />
            <StylizedInput
                id="website"
                label="Website"
                disabled={isLoading}
                register={register}
                errors={errors}
            />
        </div>
    );

    return (
        <Modal
            disabled={isLoading}
            isOpen={socialDataModal.isOpen}
            title="Edit Social Data"
            actionLabel="Continue"
            onClose={socialDataModal.onClose}
            onSubmit={handleSubmit(onSubmit)}
            body={bodyContent}
        />
    );
};

export default EditSocialDataModal;
