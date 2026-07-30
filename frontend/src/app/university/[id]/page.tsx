// School detail route — /university/[id]
//
// The app requires a server runtime for its Preview BFF, so school
// details are resolved on demand through the existing DataSource.
// Unknown IDs therefore follow the same fail-closed runtime path.

import { UniversityDetailView } from "@/components/university/UniversityDetailView";

export const dynamic = "force-dynamic";
export const dynamicParams = true;

export default function UniversityDetailPage() {
  return <UniversityDetailView />;
}
