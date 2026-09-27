// Board logic of the bundled Lovelace card: which beds light up for a dart.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  bedPath,
  beds,
  boardSvg,
  cssColor,
  escapeHtml,
  kind,
  label,
  NORM,
  NUMBERS,
  numbersSvg,
  parseSegment,
  pastSessions,
  R,
  recentVisits,
  sectorAt,
  shortProcessor,
} from "../../custom_components/autodarts/frontend/autodarts-card.js";

const hass = { locale: { language: "en" } };
const dart = (number, multiplier, bed, extra = {}) => ({ number, multiplier, bed, ...extra });

test("board order and geometry match a standard board", () => {
  assert.deepEqual(NUMBERS.slice(0, 5), [20, 1, 18, 4, 13]);
  assert.equal(new Set(NUMBERS).size, 20);
  assert.equal(R.doubleOut, NORM);
  assert.ok(R.bull < R.outerBull && R.outerBull < R.trebleIn && R.trebleOut < R.doubleIn);
});

test("scoring beds are highlighted from the reported bed", () => {
  assert.deepEqual(beds(dart(20, 3, "Triple")), ["T20"]);
  assert.deepEqual(beds(dart(16, 2, "Double")), ["D16"]);
  assert.deepEqual(beds(dart(5, 1, "SingleInner")), ["SI5"]);
  assert.deepEqual(beds(dart(5, 1, "SingleOuter")), ["SO5"]);
  assert.deepEqual(beds(dart(25, 2, "Double")), ["Bull"]);
  assert.deepEqual(beds(dart(25, 1, "Single")), ["25"]);
});

test("single beds fall back to the dart position, then to both beds", () => {
  assert.deepEqual(beds(dart(20, 1, null, { x: 0, y: 0.4 })), ["SI20"]);
  assert.deepEqual(beds(dart(20, 1, null, { x: 0, y: 0.8 })), ["SO20"]);
  assert.deepEqual(beds(dart(20, 1, "Single")), ["SI20", "SO20"]);
  assert.deepEqual(beds(dart(20, 3, null)), ["T20"]);
});

test("misses light up the outer ring of their sector", () => {
  assert.deepEqual(beds(dart(3, 0, "Outside")), ["M3"]);
  // Straight down from the bull is the 3; to the right is the 6.
  assert.deepEqual(beds(dart(0, 0, "Outside", { x: 0, y: -1.1 })), ["M3"]);
  assert.deepEqual(beds(dart(0, 0, "Outside", { x: 1.1, y: 0 })), ["M6"]);
  assert.deepEqual(beds(dart(0, 0, "Outside")), ["Miss"]);
  assert.equal(sectorAt({ x: 0, y: 1 }), 20);
  assert.equal(sectorAt({ x: Number.NaN, y: 1 }), null);
});

test("unknown numbers are never highlighted", () => {
  assert.deepEqual(beds(dart(21, 1, "SingleOuter")), []);
  assert.equal(bedPath("T21"), null);
  assert.equal(bedPath("<script>"), null);
});

test("every bed has a closed SVG path", () => {
  for (const number of NUMBERS) {
    for (const bed of ["SI", "T", "SO", "D", "M"]) {
      assert.match(bedPath(`${bed}${number}`), /^M.*Z$/);
    }
  }
  for (const id of ["Bull", "25", "Miss"]) assert.match(bedPath(id), /^M.*Z$/);
});

test("labels and kinds describe the dart", () => {
  assert.equal(label(hass, dart(20, 3, "Triple")), "T20");
  assert.equal(label(hass, dart(16, 2, "Double")), "D16");
  assert.equal(label(hass, dart(7, 1, "SingleOuter")), "S7");
  assert.equal(label(hass, dart(25, 2, "Double")), "Bull");
  assert.equal(label(hass, dart(25, 1, "Single")), "25");
  assert.equal(label(hass, dart(3, 0, "Outside")), "Miss");
  assert.equal(label({ locale: { language: "de" } }, dart(3, 0, "Outside")), "Fehlwurf");
  assert.equal(kind(dart(20, 3, "Triple")), "triple");
  assert.equal(kind(dart(25, 1, "Single")), "outer-bull");
  assert.equal(kind(dart(0, 0, "Outside")), "miss");
});

test("segment names from older integrations are parsed", () => {
  assert.deepEqual(parseSegment("T20"), { number: 20, multiplier: 3 });
  assert.deepEqual(parseSegment("d16"), { number: 16, multiplier: 2 });
  assert.deepEqual(parseSegment("Bull"), { number: 25, multiplier: 2 });
  assert.deepEqual(parseSegment("25"), { number: 25, multiplier: 1 });
  assert.deepEqual(parseSegment("M3"), { number: 3, multiplier: 0 });
  assert.equal(parseSegment("unknown"), null);
  assert.equal(parseSegment(null), null);
});

test("the board has 80 bed segments, both bulls and 20 numbers", () => {
  for (const style of ["classic", "autodarts", "unknown"]) {
    assert.equal(boardSvg(style).match(/<path /g).length, 80);
    assert.equal(boardSvg(style).match(/<circle /g).length >= 3, true);
    assert.equal(numbersSvg(style).match(/<text /g).length, 20);
  }
});

test("text inserted into the card is escaped", () => {
  assert.equal(escapeHtml(`<img src=x onerror="a">&'`), "&#60;img src=x onerror=&#34;a&#34;&#62;&#38;&#39;");
  assert.equal(escapeHtml(null), "");
});

test("colour options reach the style only as valid colours", (t) => {
  // Without a CSS object model nothing is trusted.
  assert.equal(cssColor("#00e5ff", "fallback"), "fallback");
  // Colour names of Home Assistant's picker follow the theme, also without CSS.supports.
  assert.equal(cssColor("primary", "fallback"), "var(--primary-color)");
  assert.equal(cssColor("red", "fallback"), "var(--red-color)");
  assert.equal(cssColor("deep-orange", "fallback"), "var(--deep-orange-color)");
  // Node has none; mimic the browser for a few known values.
  const valid = new Set(["#ff0000", "rgb(1, 2, 3)", "var(--primary-color)", "crimson"]);
  globalThis.CSS = { supports: (property, value) => property === "color" && valid.has(value) };
  t.after(() => delete globalThis.CSS);
  for (const value of valid) assert.equal(cssColor(value, "fallback"), value);
  for (const value of ["url(https://example.com/x.png)", "red; background: blue", "", 42, null, undefined]) {
    assert.equal(cssColor(value, "fallback"), "fallback");
  }
  // The browser accepts any var() with a fallback, and escapes hide a url(): neither reaches the style.
  globalThis.CSS = { supports: () => true };
  assert.equal(cssColor("var(--my-accent)", "fallback"), "var(--my-accent)");
  for (const value of [
    "var(--x, image-set('https://host/p.png' 1x))",
    "var(--x, red)",
    String.raw`u\72l(https://host/p.png)`,
    "src('https://host/p.png')",
    "-webkit-image-set(x)",
  ]) {
    assert.equal(cssColor(value, "fallback"), "fallback");
  }
});

test("recent visits keep valid entries, newest first, at most five", () => {
  const visits = [
    { time: "t", score: 180, darts: 3, segments: ["T20", "T20", "T20"] },
    { score: "140", segments: [] },
    { score: 60.4, segments: ["T20", 5, null] },
    null,
    { score: -1, segments: [] },
    ...Array.from({ length: 6 }, (_, index) => ({ score: index, segments: [] })),
  ];
  const result = recentVisits(visits);
  assert.equal(result.length, 5);
  assert.deepEqual(result[0], { score: 180, segments: ["T20", "T20", "T20"] });
  assert.deepEqual(result[1], { score: 60, segments: ["T20"] });
  assert.deepEqual(recentVisits("junk"), []);
});

test("past sessions need an end time and darts", () => {
  const sessions = [
    { ended: "2026-09-26T18:40:00+00:00", duration_minutes: 42.5, darts: 90, average: 55.27, highest_visit: 140 },
    { ended: "2026-09-26T17:00:00+00:00", darts: 0, average: null },
    { ended: "yesterday", darts: 3 },
    { ended: "2026-09-25T20:00:00+00:00", darts: 12, average: "x", highest_visit: null },
  ];
  assert.deepEqual(pastSessions(sessions), [
    { ended: Date.parse("2026-09-26T18:40:00+00:00"), minutes: 42.5, darts: 90, average: 55.27, best: 140 },
    { ended: Date.parse("2026-09-25T20:00:00+00:00"), minutes: null, darts: 12, average: null, best: null },
  ]);
  assert.deepEqual(pastSessions(undefined), []);
  assert.equal(pastSessions(Array(9).fill(sessions[0]), 5).length, 5);
});

test("processor names drop trademarks and clock speed", () => {
  assert.equal(shortProcessor("Intel(R) Core(TM) i3-9100T CPU @ 3.10GHz"), "Intel Core i3-9100T");
  assert.equal(shortProcessor("AMD Ryzen 5 5600G with Radeon Graphics"), "AMD Ryzen 5 5600G with Radeon Graphics");
  assert.equal(shortProcessor("Cortex-A76 @ 2.4GHz"), "Cortex-A76");
  assert.equal(shortProcessor(null), "");
});
