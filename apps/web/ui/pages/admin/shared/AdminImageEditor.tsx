"use client";

import { ExternalLink, Save, Trash2, Upload, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/ui/components/ui/button";

export type AdminImageEditorStatus = {
    kind: "idle" | "ok" | "error";
    message?: string;
};

type Props = {
    id: string;
    title: string;
    currentImage?: { url: string; alt: string; className: string };
    emptyClassName: string;
    urlInput: {
        label: string;
        ariaLabel: string;
        value: string;
        placeholder: string;
        saveAriaLabel: string;
        canSave: boolean;
        onChange: (value: string) => void;
        onSave: () => void;
    };
    fileInput: {
        ariaLabel: string;
        chooseLabel: string;
        guidance: string;
        stagedFile: File | null;
        pendingLabel: string;
        pendingAlt: string;
        previewClassName: string;
        onSelect: (file: File) => void | Promise<void>;
        onPublish: () => void;
        onDiscard: () => void;
    };
    status?: AdminImageEditorStatus;
    disabled: boolean;
    remove?: { visible: boolean; label: string; onRemove: () => void };
};

const ACCEPTED_IMAGE_TYPES =
    "image/jpeg,image/png,image/webp,image/avif,image/gif";

function StagedImagePreview({
    file,
    alt,
    className,
}: {
    file: File;
    alt: string;
    className: string;
}) {
    const [src, setSrc] = useState("");

    useEffect(() => {
        const objectUrl = URL.createObjectURL(file);
        setSrc(objectUrl);
        return () => URL.revokeObjectURL(objectUrl);
    }, [file]);

    if (!src) return null;
    return <img src={src} alt={alt} className={className} />;
}

export function AdminImageEditor({
    id,
    title,
    currentImage,
    emptyClassName,
    urlInput,
    fileInput,
    status,
    disabled,
    remove,
}: Props) {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const urlInputId = `${id}-url`;
    const fileInputId = `${id}-file`;

    return (
        <div className="space-y-3 rounded-md border border-copper/20 bg-surface-elevated/80 p-3">
            <div className="flex items-center justify-between gap-2">
                <div className="font-dmSans text-caption font-semibold uppercase tracking-wide text-muted-foreground">
                    {title}
                </div>
                {currentImage ? (
                    <a
                        href={currentImage.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 font-dmSans text-caption font-semibold text-copper-dark hover:underline"
                    >
                        Open
                        <ExternalLink
                            className="h-3.5 w-3.5"
                            aria-hidden="true"
                        />
                    </a>
                ) : null}
            </div>
            {currentImage ? (
                <img
                    src={currentImage.url}
                    alt={currentImage.alt}
                    className={currentImage.className}
                />
            ) : fileInput.stagedFile ? null : (
                <div className={emptyClassName}>Empty</div>
            )}
            <div className="grid gap-1">
                <label
                    htmlFor={urlInputId}
                    className="font-dmSans text-caption font-semibold uppercase tracking-wide text-muted-foreground"
                >
                    {urlInput.label}
                </label>
                <div className="flex flex-wrap gap-2 sm:flex-nowrap">
                    <input
                        id={urlInputId}
                        aria-label={urlInput.ariaLabel}
                        type="url"
                        value={urlInput.value}
                        onChange={(event) =>
                            urlInput.onChange(event.target.value)
                        }
                        placeholder={urlInput.placeholder}
                        className="w-full min-w-0 flex-1 rounded-md border border-input bg-background px-3 py-2 font-dmSans text-body normal-case tracking-normal text-foreground outline-none placeholder:text-muted-foreground focus:border-copper focus:ring-2 focus:ring-copper/30"
                    />
                    <Button
                        type="button"
                        variant="outline"
                        aria-label={urlInput.saveAriaLabel}
                        className="shrink-0 gap-2 border-copper/40 bg-surface-elevated text-foreground hover:bg-copper/10 disabled:border-strong disabled:bg-surface-muted disabled:text-muted-foreground disabled:opacity-100"
                        disabled={disabled || !urlInput.canSave}
                        onClick={urlInput.onSave}
                    >
                        <Save className="h-4 w-4" aria-hidden="true" />
                        Save URL
                    </Button>
                </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
                <input
                    ref={fileInputRef}
                    id={fileInputId}
                    aria-label={fileInput.ariaLabel}
                    type="file"
                    accept={ACCEPTED_IMAGE_TYPES}
                    className="sr-only"
                    onChange={(event) => {
                        const file = event.currentTarget.files?.[0] ?? null;
                        event.currentTarget.value = "";
                        if (file) void fileInput.onSelect(file);
                    }}
                />
                <Button
                    type="button"
                    variant="outline"
                    className="gap-2 border-copper/40 bg-surface-elevated text-foreground hover:bg-copper/10 disabled:border-strong disabled:bg-surface-muted disabled:text-muted-foreground disabled:opacity-100"
                    disabled={disabled}
                    onClick={() => fileInputRef.current?.click()}
                >
                    <Upload className="h-4 w-4" aria-hidden="true" />
                    {fileInput.chooseLabel}
                </Button>
                <span className="font-dmSans text-caption normal-case tracking-normal text-muted-foreground">
                    {fileInput.guidance}
                </span>
            </div>
            {fileInput.stagedFile ? (
                <div className="inline-flex max-w-full flex-wrap items-center gap-3 rounded-md border border-copper/30 bg-surface-muted/30 p-3">
                    <StagedImagePreview
                        file={fileInput.stagedFile}
                        alt={fileInput.pendingAlt}
                        className={fileInput.previewClassName}
                    />
                    <div className="grid min-w-[220px] flex-1 gap-2">
                        <div>
                            <div className="font-dmSans text-caption font-semibold uppercase tracking-wide text-muted-foreground">
                                {fileInput.pendingLabel}
                            </div>
                            <div className="font-dmSans text-caption text-muted-foreground">
                                Publish the staged file or discard it before
                                choosing another.
                            </div>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            <Button
                                type="button"
                                className="gap-2 bg-copper-dark text-white hover:bg-cedar disabled:bg-surface-muted disabled:text-muted-foreground disabled:opacity-100"
                                disabled={disabled}
                                onClick={fileInput.onPublish}
                            >
                                <Upload
                                    className="h-4 w-4"
                                    aria-hidden="true"
                                />
                                Publish to Bunny
                            </Button>
                            <Button
                                type="button"
                                variant="outline"
                                className="gap-2 border-strong bg-surface-elevated text-foreground hover:bg-surface-muted"
                                disabled={disabled}
                                onClick={fileInput.onDiscard}
                            >
                                <X className="h-4 w-4" aria-hidden="true" />
                                Discard
                            </Button>
                        </div>
                    </div>
                </div>
            ) : null}
            {status?.message ? (
                <p
                    role={status.kind === "error" ? "alert" : "status"}
                    className={
                        status.kind === "error"
                            ? "rounded-md border border-red-700/30 bg-red-50 px-3 py-2 font-dmSans text-caption font-semibold text-red-900"
                            : "rounded-md border border-green-700/30 bg-green-50 px-3 py-2 font-dmSans text-caption font-semibold text-green-900"
                    }
                >
                    {status.message}
                </p>
            ) : null}
            {remove?.visible ? (
                <Button
                    type="button"
                    variant="outline"
                    className="gap-2 border-red-800/40 bg-surface-elevated text-red-950 hover:bg-red-50 disabled:border-strong disabled:bg-surface-muted disabled:text-muted-foreground disabled:opacity-100"
                    disabled={disabled}
                    onClick={remove.onRemove}
                >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                    {remove.label}
                </Button>
            ) : null}
        </div>
    );
}
