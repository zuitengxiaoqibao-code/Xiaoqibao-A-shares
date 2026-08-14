const SECTOR_PALETTE = [
  "#5cc8ff",
  "#b58cff",
  "#f3c969",
  "#5ee0b3",
  "#ff9a68",
  "#8fa8ff",
  "#e889d5",
  "#86d7de",
  "#d6a2ff",
  "#f2a7b8",
] as const;

export function sectorColor(sectorCode: string, fallbackIndex = 0): string {
  let hash = fallbackIndex | 0;
  for (let index = 0; index < sectorCode.length; index += 1) {
    hash = (hash * 31 + sectorCode.charCodeAt(index)) | 0;
  }
  return SECTOR_PALETTE[Math.abs(hash) % SECTOR_PALETTE.length];
}
