import type { Metadata } from "next";
import Image from "next/image";
import { notFound } from "next/navigation";
import path from "node:path";
import { readdir, readFile } from "node:fs/promises";
import { isLocalDevelopment } from "./access";
import styles from "./page.module.css";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export const metadata: Metadata = {
    title: "App Store Submission Review",
    description:
        "A local-only view of the exact Laughtrack Fastlane submission inputs.",
    robots: { index: false, follow: false },
};

const FASTLANE_ROOT = path.resolve(process.cwd(), "../../ios/fastlane");
const LOCALE_ROOT = path.join(FASTLANE_ROOT, "metadata/en-US");
const REVIEW_ROOT = path.join(FASTLANE_ROOT, "metadata/review_information");
const SCREENSHOT_ROOT = path.join(FASTLANE_ROOT, "screenshots/en-US");

const metadataFields = [
    { key: "name", label: "App name", limit: 30 },
    { key: "subtitle", label: "Subtitle", limit: 30 },
    { key: "promotional_text", label: "Promotional text", limit: 170 },
    { key: "description", label: "Description", limit: 4000 },
    { key: "keywords", label: "Keywords", limit: 100 },
    { key: "release_notes", label: "What’s New", limit: 4000 },
    { key: "marketing_url", label: "Marketing URL" },
    { key: "support_url", label: "Support URL" },
    { key: "privacy_url", label: "Privacy policy URL" },
] as const;

async function readText(filePath: string) {
    return (await readFile(filePath, "utf8")).trim();
}

async function loadSubmission() {
    const fields = await Promise.all(
        metadataFields.map(async (field) => ({
            ...field,
            value: await readText(path.join(LOCALE_ROOT, `${field.key}.txt`)),
        })),
    );
    const [
        copyright,
        primaryCategory,
        secondaryCategory,
        firstName,
        lastName,
        email,
        phone,
        notes,
    ] = await Promise.all([
        readText(path.join(FASTLANE_ROOT, "metadata/copyright.txt")),
        readText(path.join(FASTLANE_ROOT, "metadata/primary_category.txt")),
        readText(path.join(FASTLANE_ROOT, "metadata/secondary_category.txt")),
        readText(path.join(REVIEW_ROOT, "first_name.txt")),
        readText(path.join(REVIEW_ROOT, "last_name.txt")),
        readText(path.join(REVIEW_ROOT, "email_address.txt")),
        readText(path.join(REVIEW_ROOT, "phone_number.txt")),
        readText(path.join(REVIEW_ROOT, "notes.txt")),
    ]);
    const screenshots = (await readdir(SCREENSHOT_ROOT))
        .filter((filename) => filename.endsWith(".png"))
        .sort((left, right) => left.localeCompare(right));

    return {
        fields,
        copyright,
        primaryCategory,
        secondaryCategory,
        review: { firstName, lastName, email, phone, notes },
        screenshots,
    };
}

function FieldStatus({ value, limit }: { value: string; limit?: number }) {
    if (!limit) return <span>{value.length} characters</span>;
    const isOver = value.length > limit;
    return (
        <span className={isOver ? styles.overLimit : undefined}>
            {value.length} / {limit} characters
        </span>
    );
}

function MetadataField({
    label,
    value,
    limit,
}: {
    label: string;
    value: string;
    limit?: number;
}) {
    const isLong = label === "Description" || label === "What’s New";
    const isWarning =
        label === "What’s New" &&
        /\[TASK-|update ios .*release notes/i.test(value);

    return (
        <article
            className={`${styles.field} ${isLong ? styles.fieldWide : ""}`}
        >
            <div className={styles.fieldHeader}>
                <h3>{label}</h3>
                <FieldStatus limit={limit} value={value} />
            </div>
            <pre>{value || "—"}</pre>
            {isWarning ? (
                <p className={styles.warningText}>
                    Review before upload: this reads like internal task text,
                    not customer-facing release notes.
                </p>
            ) : null}
        </article>
    );
}

function ScreenshotGroup({
    device,
    files,
}: {
    device: string;
    files: string[];
}) {
    return (
        <section className={styles.deviceGroup}>
            <div className={styles.deviceHeading}>
                <div>
                    <p className={styles.eyebrow}>Upload directory</p>
                    <h3>{device}</h3>
                </div>
                <span>
                    {files.length} PNG files · 1320 × 2868 shown where
                    applicable
                </span>
            </div>
            <div className={styles.screenshotRail}>
                {files.map((filename, index) => {
                    const source = `/app-store-storyboard/screenshot/${encodeURIComponent(filename)}`;
                    const captureName = filename
                        .replace(/^.*?-/, "")
                        .replace(/\.png$/, "");
                    const isIpad = filename.startsWith("iPad");
                    return (
                        <article
                            className={`${styles.screenshotCard} ${isIpad ? styles.ipadCard : ""}`}
                            key={filename}
                        >
                            <div className={styles.screenshotMeta}>
                                <span>
                                    {String(index + 1).padStart(2, "0")}
                                </span>
                                <strong>{captureName}</strong>
                            </div>
                            <a
                                href={source}
                                target="_blank"
                                rel="noreferrer"
                                title={`Open original ${filename}`}
                            >
                                <Image
                                    alt={`Exact App Store submission screenshot ${captureName} for ${device}`}
                                    className={styles.screenshot}
                                    height={isIpad ? 2752 : 2868}
                                    priority={index < 2 && !isIpad}
                                    sizes={isIpad ? "420px" : "270px"}
                                    src={source}
                                    unoptimized
                                    width={isIpad ? 2064 : 1320}
                                />
                            </a>
                            <code>{filename}</code>
                        </article>
                    );
                })}
            </div>
        </section>
    );
}

export default async function AppStoreStoryboardPage() {
    if (!isLocalDevelopment()) notFound();

    const submission = await loadSubmission();
    const iphoneScreenshots = submission.screenshots.filter((filename) =>
        filename.startsWith("iPhone"),
    );
    const ipadScreenshots = submission.screenshots.filter((filename) =>
        filename.startsWith("iPad"),
    );
    const whatsNew =
        submission.fields.find((field) => field.key === "release_notes")
            ?.value ?? "";
    const hasReleaseNotesWarning = /\[TASK-|update ios .*release notes/i.test(
        whatsNew,
    );

    return (
        <main id="main-content" className={styles.page}>
            <header className={styles.header}>
                <div className={styles.topline}>
                    <span className={styles.localBadge}>Local only</span>
                    <code>ios/fastlane</code>
                </div>
                <div className={styles.titleRow}>
                    <div>
                        <p className={styles.eyebrow}>
                            Literal Fastlane inputs
                        </p>
                        <h1>App Store submission review</h1>
                    </div>
                    <p>
                        No mockups. No captions. No transformed images. This
                        page reads the exact files that Fastlane’s{" "}
                        <code>deliver</code> lanes send to App Store Connect.
                    </p>
                </div>
            </header>

            <section className={styles.summary} aria-label="Submission summary">
                <div>
                    <span>Bundle ID</span>
                    <strong>app.laughtrack.ios</strong>
                </div>
                <div>
                    <span>Locale</span>
                    <strong>en-US</strong>
                </div>
                <div>
                    <span>Screenshot files</span>
                    <strong>{submission.screenshots.length}</strong>
                </div>
                <div>
                    <span>Upload behavior</span>
                    <strong>Overwrite screenshots</strong>
                </div>
                <div>
                    <span>Review account</span>
                    <strong>Not required</strong>
                </div>
            </section>

            {hasReleaseNotesWarning ? (
                <aside className={styles.alert}>
                    <strong>One submission blocker is visible.</strong>
                    <span>
                        <code>release_notes.txt</code> currently contains a task
                        ID and placeholder-style copy. It should be rewritten
                        before sending metadata to Apple.
                    </span>
                </aside>
            ) : null}

            {ipadScreenshots.length ? (
                <aside className={styles.notice}>
                    <strong>Confirm the iPad upload set.</strong>
                    <span>
                        The Snapfile describes iPad as a comparison profile, but{" "}
                        {ipadScreenshots.length} iPad PNGs are in the same
                        screenshot directory that <code>deliver</code> reads.
                        The shipping target is iPhone-only, so these should be
                        explicitly confirmed or excluded before submission.
                    </span>
                </aside>
            ) : null}

            <section className={styles.section}>
                <div className={styles.sectionHeading}>
                    <div>
                        <p className={styles.eyebrow}>Store listing · en-US</p>
                        <h2>Customer-facing metadata</h2>
                    </div>
                    <p>
                        Values and character counts are read directly from each
                        Fastlane text file.
                    </p>
                </div>
                <div className={styles.metadataGrid}>
                    {submission.fields.map((field) => (
                        <MetadataField
                            key={field.key}
                            label={field.label}
                            limit={"limit" in field ? field.limit : undefined}
                            value={field.value}
                        />
                    ))}
                </div>
            </section>

            <section className={styles.section}>
                <div className={styles.sectionHeading}>
                    <div>
                        <p className={styles.eyebrow}>Unmodified PNGs</p>
                        <h2>Screenshots in the upload set</h2>
                    </div>
                    <p>
                        Click any image to open the original file at full
                        resolution. Ordering follows the filenames in{" "}
                        <code>fastlane/screenshots/en-US</code>.
                    </p>
                </div>
                <ScreenshotGroup
                    device="iPhone 16 Pro Max"
                    files={iphoneScreenshots}
                />
                {ipadScreenshots.length ? (
                    <ScreenshotGroup
                        device="iPad Pro 13-inch (M4)"
                        files={ipadScreenshots}
                    />
                ) : null}
            </section>

            <section className={styles.section}>
                <div className={styles.sectionHeading}>
                    <div>
                        <p className={styles.eyebrow}>App classification</p>
                        <h2>Categories and ownership</h2>
                    </div>
                </div>
                <div className={styles.compactGrid}>
                    <MetadataField
                        label="Primary category"
                        value={submission.primaryCategory}
                    />
                    <MetadataField
                        label="Secondary category"
                        value={submission.secondaryCategory}
                    />
                    <MetadataField
                        label="Copyright"
                        value={submission.copyright}
                    />
                </div>
            </section>

            <section className={styles.section}>
                <div className={styles.sectionHeading}>
                    <div>
                        <p className={styles.eyebrow}>Private · local view</p>
                        <h2>App Review information</h2>
                    </div>
                    <p>
                        This section is deliberately blocked from production
                        because it contains review contact details.
                    </p>
                </div>
                <div className={styles.reviewGrid}>
                    <MetadataField
                        label="Review contact"
                        value={`${submission.review.firstName} ${submission.review.lastName}\n${submission.review.email}\n${submission.review.phone}`}
                    />
                    <MetadataField
                        label="Review notes"
                        limit={4000}
                        value={submission.review.notes}
                    />
                </div>
            </section>

            <section className={styles.delivery}>
                <div>
                    <p className={styles.eyebrow}>Fastlane behavior</p>
                    <h2>What happens when it runs</h2>
                </div>
                <ul>
                    <li>
                        <strong>upload_metadata</strong>
                        <span>
                            Uploads metadata and screenshots, replaces existing
                            screenshots, and does not upload a binary.
                        </span>
                    </li>
                    <li>
                        <strong>upload_app_store</strong>
                        <span>
                            Uploads the IPA, metadata, and screenshots together,
                            but does not submit for review.
                        </span>
                    </li>
                    <li>
                        <strong>submit_review</strong>
                        <span>
                            Uploads metadata and screenshots and submits the
                            prepared version for App Review.
                        </span>
                    </li>
                </ul>
            </section>
        </main>
    );
}
