# Monitor Console Homepage Design

## Mode

Redesign-preserve. Keep routes, navigation labels, accessibility semantics, decision data flow, market sentiment, and the three decision phases. Replace only the homepage composition and visual language.

## Reference Boundary

Use the supplied screenshot only for layout and visual character: deep navy canvas, blue window title bars, thin cyan borders, compact monitoring panes, square geometry, and dense status information. Do not reproduce any screenshot text, video controls, subtitles, watermarks, social buttons, counters, or overlays.

## Design Read

- Artifact: operational A-share decision dashboard.
- Audience: a beginner who wants expert-looking structure without losing plain-language guidance.
- Visual language: institutional monitoring console with scientific instrumentation cues.
- Preserve: six navigation entries, independent convertible-bond route, market/selected-stock scope, sentiment dashboard, and premarket/intraday/postclose workbench.
- Improve: homepage hierarchy, pane rhythm, visual density, professional status encoding, and first-viewport information flow.
- Remove: soft card presentation, loose vertical spacing, decorative gradients, and large empty areas.

## Design System

- Canvas: `#06131C`.
- Deep panel: `#081A25`.
- Window surface: `#0C2230`.
- Window title: `#154D78`.
- Border: `#1E5874`.
- Signal cyan: `#43D6E4`.
- Ready green: `#53D6AC`.
- Warning amber: `#E9BD62`.
- Risk red: `#FF7486`.
- Primary text: `#DCEEF4`.
- Muted text: `#7695A3`.
- Radius: 0 to 2px. No shadows. Elevation uses borders and title bars.
- Typography: Chinese UI uses the existing readable sans stack; labels and numerical data use Consolas/monospace with tabular numerals.
- Motion: state feedback only, 120-160ms. Respect reduced motion.

## Layout

The homepage becomes a monitoring deck inside the existing global navigation contract:

1. A compact system bar introduces A-share decision monitoring and true product constraints.
2. The scope selector is integrated into the control band.
3. The market sentiment dashboard occupies the first primary window.
4. The three-phase decision workbench occupies the second primary window.
5. Existing phase, evidence, risk, and quality content becomes the lower dense pane system through scoped CSS rather than duplicated content.

Desktop uses a stable monitoring grid. Tablet and mobile collapse into a single column while preserving tab order, headings, and touch targets.

## Testing

- Add a homepage structure test for the monitoring region, control bar, market window, and decision window.
- Preserve all existing dashboard and decision tests.
- Run browser visual acceptance at 1440x900, 1280x720, and 390x844.
- Run production build, full frontend tests, diff checks, and UTF-8/mojibake scans.
