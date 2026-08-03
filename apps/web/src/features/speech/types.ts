export type SpeechSettings = {
  voice: string;
  rate: number;
};

export type SpeechVoice = {
  id: string;
  label: string;
  gender: "female" | "male";
};

export type SpeechVoiceCatalog = {
  voices: SpeechVoice[];
};

export type SpeechSynthesisInput = {
  text: string;
  voice?: string;
  rate?: number;
};

export type SpeechSettingsLoader = (signal?: AbortSignal) => Promise<SpeechSettings>;
export type SpeechSettingsSaver = (
  input: SpeechSettings,
  signal?: AbortSignal,
) => Promise<SpeechSettings>;
export type SpeechVoiceLoader = (signal?: AbortSignal) => Promise<SpeechVoiceCatalog>;
export type SpeechSynthesizer = (
  input: SpeechSynthesisInput,
  signal?: AbortSignal,
) => Promise<Blob>;
