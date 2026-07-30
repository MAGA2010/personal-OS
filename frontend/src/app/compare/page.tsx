import { redirect } from "next/navigation";

/**
 * The canonical university comparison experience lives inside `/map`.
 * Keep `/compare` as a stable public entry without duplicating data or UI.
 */
export default function CompareEntryPage() {
  redirect("/map");
}
