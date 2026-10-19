/** Curation state is independent of public visibility and worker processing. */
export type EntityKind = "comedian" | "club" | "show" | "podcast";
export type EntityDisposition = "pending" | "approved" | "blocked";
export type RelationshipDisposition =
    | "proposed"
    | "confirmed"
    | "rejected"
    | "severed";
export type ProcessingState =
    | "pending"
    | "applied"
    | "conflict"
    | "failed"
    | "canceled";
export type EntityAction = "approve" | "block" | "restore";
export type RelationshipAction = "confirm" | "reject" | "sever" | "restore";
export type CurationTarget =
    | { type: "entity"; id: string; kind: EntityKind }
    | {
          type: "relationship";
          id: string;
          kind: "alias_of" | "host_of" | "cohost_of";
      };

export function entityTransition(
    state: EntityDisposition,
    action: EntityAction,
): EntityDisposition {
    if (state === "pending" && action === "approve") return "approved";
    if ((state === "pending" || state === "approved") && action === "block")
        return "blocked";
    if (state === "blocked" && action === "restore") return "pending";
    throw new Error(`Invalid entity transition: ${state}/${action}`);
}
export function relationshipTransition(
    state: RelationshipDisposition,
    action: RelationshipAction,
): RelationshipDisposition {
    if (state === "proposed" && action === "confirm") return "confirmed";
    if (state === "proposed" && action === "reject") return "rejected";
    if (state === "confirmed" && action === "sever") return "severed";
    if ((state === "rejected" || state === "severed") && action === "restore")
        return "proposed";
    throw new Error(`Invalid relationship transition: ${state}/${action}`);
}
/** Versioned exact-name rule only; never evidence that two performers are the same.
 * NFC + Unicode White_Space collapse + locale-independent lowercasing.
 * Preserve punctuation, accents and word boundaries. Zero-width spaces are significant.
 */
export function normalizeExactNameV1(value: string): string {
    const normalized = value
        .normalize("NFC")
        .replace(
            // Unicode White_Space intentionally includes tab through carriage return.
            // eslint-disable-next-line no-control-regex
            /[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+/g,
            " ",
        )
        .replace(/^ +| +$/g, "")
        .toLowerCase()
        .normalize("NFC");
    if (!normalized) throw new Error("An exact-name key cannot be empty");
    return normalized;
}
export type IdentityKey = {
    entityKind: EntityKind;
    namespace: string;
    scope: string;
    value: string;
} & (
    | {
          identityScope: "entity";
          keyType: "external_id" | "legacy_id" | "feed_url";
      }
    | { identityScope: "name"; keyType: "exact_name" }
    | { identityScope: "series"; keyType: "series_id" }
);
export function validateIdentityKey(key: IdentityKey): IdentityKey {
    if (
        !/^[a-z0-9][a-z0-9_.:-]*$/.test(key.namespace) ||
        !key.scope.trim() ||
        key.scope !== key.scope.trim() ||
        !key.value.trim()
    )
        throw new Error("Invalid identity key");
    if (key.identityScope === "series" && key.entityKind !== "show")
        throw new Error("Series keys require shows");
    if (
        key.keyType === "exact_name" &&
        (key.namespace !== "exact-name:v1" ||
            key.value !== normalizeExactNameV1(key.value))
    )
        throw new Error("Exact-name keys require versioned normalization");
    return key;
}
