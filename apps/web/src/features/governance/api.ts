import type { AuditStatus, ComplianceStatus, RiskStatus } from "./GovernanceViews";
import { apiClient } from "../../shared/apiClient";
async function read<T>(url: string): Promise<T> { return apiClient.get<T>(url, { context: "治理服务" }); }
export const loadRisk = () => read<RiskStatus>("/api/v1/xingbu/status"); export const loadCompliance = (asset = "a_share") => read<ComplianceStatus>(`/api/v1/libu/status?asset=${asset}`); export const loadAudit = () => read<AuditStatus>("/api/v1/dongchang/findings");
export async function complianceAction(source: string, action: string, permissionReference?: string, asset = "a_share"): Promise<Record<string, unknown>> { return apiClient.post(`/api/v1/libu/sources/${source}/${action}?asset=${asset}`, { permission_reference: permissionReference?.trim() || `explicit-${action}` }, { context: "合规操作" }); }
