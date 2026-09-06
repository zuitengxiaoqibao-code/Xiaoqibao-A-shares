export type SectorHighlightRow = {
  sector_id: string;
  name: string;
  leaderName?: string | null;
  change_percent: string | number | null;
  rising_count: number;
  falling_count: number;
  amount_yi: string | number | null;
};

export function sectorHighlightSignature(sector: SectorHighlightRow): string {
  return JSON.stringify([
    sector.sector_id,
    sector.name,
    sector.leaderName ?? null,
    sector.change_percent,
    sector.rising_count,
    sector.falling_count,
    sector.amount_yi,
  ]);
}

export function findChangedSectorIds(
  previous: Map<string, string> | null,
  sectors: SectorHighlightRow[],
): string[] {
  if (!previous) return [];
  return sectors
    .filter((sector) => previous.get(sector.sector_id) !== sectorHighlightSignature(sector))
    .map((sector) => sector.sector_id);
}
