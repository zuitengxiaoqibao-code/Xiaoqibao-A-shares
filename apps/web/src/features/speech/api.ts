import type {
  SpeechSettings,
  SpeechSynthesisInput,
  SpeechVoiceCatalog,
} from "./types";


async function speechJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) throw new Error(`语音服务请求失败 (${response.status})`);
  return response.json() as Promise<T>;
}

export const loadSpeechSettings = (signal?: AbortSignal) =>
  speechJson<SpeechSettings>("/api/v1/speech/settings", { signal });

export const saveSpeechSettings = (input: SpeechSettings, signal?: AbortSignal) =>
  speechJson<SpeechSettings>("/api/v1/speech/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    signal,
  });

export const loadSpeechVoices = (signal?: AbortSignal) =>
  speechJson<SpeechVoiceCatalog>("/api/v1/speech/voices", { signal });

export const synthesizeSpeech = async (
  input: SpeechSynthesisInput,
  signal?: AbortSignal,
): Promise<Blob> => {
  const response = await fetch("/api/v1/speech/synthesize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    signal,
  });
  if (!response.ok) throw new Error(`语音合成暂不可用 (${response.status})`);
  return response.blob();
};
