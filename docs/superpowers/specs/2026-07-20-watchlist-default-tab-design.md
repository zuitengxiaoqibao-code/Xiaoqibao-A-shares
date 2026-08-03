# Watchlist Default Tab Design

## Goal

Make the A-share selector open on the user's watchlist and place that tab before the generated candidate lists.

## Behavior

- Tab order is Watchlist, Short-term candidates, Swing candidates.
- Watchlist is selected on first render, including when it is empty.
- Left and right arrow navigation follows the visible tab order.
- Candidate loading, candidate selection fallback, scoring, search, and watchlist persistence remain unchanged.

## Testing

Add a focused selector test that asserts the DOM tab order, the default selected tab, and the linked watchlist panel. Keep the existing keyboard-navigation coverage and update its starting tab to match the new default.
