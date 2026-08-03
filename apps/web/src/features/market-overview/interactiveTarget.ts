import type { KeyboardEvent } from "react";

type InteractiveTargetProps = {
  role?: "link";
  tabIndex?: number;
  "aria-label"?: string;
  "data-overview-action"?: "true";
  onClick?: () => void;
  onKeyDown?: (event: KeyboardEvent<HTMLElement>) => void;
};

export function interactiveTargetProps(
  onActivate: (() => void) | undefined,
  ariaLabel: string,
): InteractiveTargetProps {
  if (!onActivate) return {};
  return {
    role: "link",
    tabIndex: 0,
    "aria-label": ariaLabel,
    "data-overview-action": "true",
    onClick: onActivate,
    onKeyDown: (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      onActivate();
    },
  };
}
