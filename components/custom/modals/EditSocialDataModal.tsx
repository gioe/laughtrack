"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import useSocialDataModal from "../../../hooks/useSocialDataModal";
import Modal from "./Modal";
import { z } from "zod";

import toast from "react-hot-toast";
import axios from "axios";
import { Comedian } from "../../../objects/classes/comedian/Comedian";
import { SocialMedia } from "../../../util/enum";
import { zodResolver } from "@hookform/resolvers/zod";
import { editSocialDataSchema } from "../../../schemas";
import SocialDataFormInput from "../form/social";

interface EditSocialDataModalProps {
    comedianString: string;
}

const All_SOCIAL_MEDIA = [
    SocialMedia.Facebook,
    SocialMedia.Instagram,
    SocialMedia.TikTok,
    SocialMedia.Twitter,
    SocialMedia.YouTube,
    SocialMedia.Website,
];

const EditSocialDataModal: React.FC<EditSocialDataModalProps> = ({
    comedianString,
}) => {
    const comedian = JSON.parse(comedianString) as Comedian;
    const socialDataModal = useSocialDataModal();
    const router = useRouter();

    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof editSocialDataSchema>>({
        resolver: zodResolver(editSocialDataSchema),
        defaultValues: {
            instagram: {
                account: comedian?.socialData?.instagram?.account ?? "",
                following: comedian?.socialData?.instagram?.following ?? 0,
            },
            tikTok: {
                account: comedian?.socialData?.tiktok?.account ?? "",
                following: comedian?.socialData?.tiktok?.following ?? 0,
            },
            facebook: {
                account: comedian?.socialData?.facebook?.account ?? "",
                following: comedian?.socialData?.facebook?.following ?? 0,
            },
            twitter: {
                account: comedian?.socialData?.twitter?.account ?? "",
                following: comedian?.socialData?.twitter?.following ?? 0,
            },
            youtube: {
                account: comedian?.socialData?.youtube?.account ?? "",
                following: comedian?.socialData?.youtube?.following ?? 0,
            },
            website: comedian?.socialData?.website ?? "",
            cardImage: undefined,
            bannerImage: undefined,
        },
    });

    const onSubmit = (data: z.infer<typeof editSocialDataSchema>) => {
        setIsLoading(true);
        console.log("SUBMITTING OVER HERE NOW");
        // axios
        //     .post("/api/editSocial", {
        //         ...data,
        //         id: comedian?.id,
        //     })
        //     .then((response) => {
        //         if (response) {
        //             setIsLoading(false);
        //             toast.success("Successfully updated");
        //             router.refresh();
        //             socialDataModal.onClose();
        //         }
        //     });
    };

    const bodyContent = (
        <div>
            {All_SOCIAL_MEDIA.map((value) => {
                return (
                    <SocialDataFormInput
                        key={value.valueOf()}
                        form={form}
                        socialMedia={value}
                    />
                );
            })}
        </div>
    );

    return (
        <Modal
            form={form}
            disabled={isLoading}
            isOpen={socialDataModal.isOpen}
            title="Edit Social Data"
            actionLabel="Continue"
            onClose={socialDataModal.onClose}
            onSubmit={onSubmit}
            body={bodyContent}
        />
    );
};

export default EditSocialDataModal;
