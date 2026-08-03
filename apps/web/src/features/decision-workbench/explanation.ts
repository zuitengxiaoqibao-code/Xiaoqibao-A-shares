import type { Advice, DecisionPhase } from "./types";

export function beginnerAdviceExplanation(
  advice: Advice,
  phase: DecisionPhase,
): string | null {
  if (phase !== "intraday") return advice.plain_language_explanation;
  const price = advice.quantitative_result.price;
  const changePercent = advice.quantitative_result.change_percent;
  if (!price?.trim() || !changePercent?.trim()) return advice.plain_language_explanation;
  const numericChange = Number(changePercent);
  if (!Number.isFinite(numericChange)) return advice.plain_language_explanation;
  const displayChange = Math.abs(numericChange) < 0.005 ? 0 : numericChange;
  const marker = "模型补充：";
  const markerIndex = advice.plain_language_explanation?.indexOf(marker) ?? -1;
  const aiSupplement = markerIndex >= 0
    ? advice.plain_language_explanation?.slice(markerIndex) ?? ""
    : "";
  return `最新价 ${price}，盘中涨跌 ${displayChange.toFixed(2)}%。当前建议是${advice.conclusion}，不是立即交易指令。${aiSupplement}`;
}
