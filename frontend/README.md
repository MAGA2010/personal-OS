# International Student & Parent Advisory MVP

This is the first website structure for the China-focused university advisory platform.

## Today Scope

- App-router Next.js shell
- Student / parent perspective toggle
- Budget-led map workspace with sample school pins
- Compare tray for up to four schools
- Advisor output panel shaped as a cited match matrix
- Data trust and correction surfaces

## Run Locally

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

## Near-Term Integration Points

- Replace `src/lib/universities.ts` with Supabase-backed data.
- Swap the visual map mock with Mapbox GL once `NEXT_PUBLIC_MAPBOX_TOKEN` is available.
- Connect the advisor panel to structured SQL retrieval before adding vector search.
- Store correction submissions in a review queue table.
