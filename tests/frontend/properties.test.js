// Property-based tests (fuzzing) of the card logic with arbitrary, hostile input.
import assert from "node:assert/strict";
import { test } from "node:test";

import fc from "fast-check";

import {
  bedPath,
  beds,
  escapeHtml,
  heatLevels,
  heatRatio,
  NUMBERS,
  parseSegment,
  pastSessions,
  recentVisits,
  sectorAt,
  topHits,
  visitBucket,
  visitsFromHistory,
} from "../../custom_components/homedarts/frontend/homedarts-card.js";

const RUNS = { numRuns: 2000 };
const BED_NAMES = ["Triple", "Double", "SingleInner", "SingleOuter", "Single", "Outside", null, "", "<b>"];

const dart = fc.record({
  number: fc.oneof(fc.integer({ min: -5, max: 30 }), fc.constantFrom(25, 50)),
  multiplier: fc.integer({ min: -1, max: 4 }),
  bed: fc.constantFrom(...BED_NAMES),
  x: fc.oneof(fc.double({ min: -2, max: 2 }), fc.constant(Number.NaN)),
  y: fc.oneof(fc.double({ min: -2, max: 2 }), fc.constant(Number.NaN)),
});

test("escaped text never contains markup and decodes back to the original", () => {
  fc.assert(
    fc.property(fc.string({ unit: "binary" }), (text) => {
      const escaped = escapeHtml(text);
      assert.ok(!/[<>"']/.test(escaped));
      assert.equal(
        escaped.replace(/&#(\d+);/g, (_, code) => String.fromCharCode(Number(code))),
        text
      );
    }),
    RUNS
  );
});

test("every highlighted bed of any dart has a drawable path", () => {
  fc.assert(
    fc.property(dart, (value) => {
      for (const id of beds(value)) assert.notEqual(bedPath(id), null, id);
    }),
    RUNS
  );
});

test("a dart position is attributed to the sector it points at", () => {
  fc.assert(
    fc.property(
      fc.integer({ min: 0, max: 19 }),
      fc.double({ min: -8.5, max: 8.5, noNaN: true }),
      fc.double({ min: 0.05, max: 1.3, noNaN: true }),
      (index, offset, radius) => {
        const angle = ((index * 18 + offset) * Math.PI) / 180;
        const point = { x: radius * Math.sin(angle), y: radius * Math.cos(angle) };
        assert.equal(sectorAt(point), NUMBERS[index]);
      }
    ),
    RUNS
  );
});

test("segment names never crash the parser and yield valid darts", () => {
  fc.assert(
    fc.property(fc.oneof(fc.string(), fc.constantFrom("T20", "D16", "Bull", "25", "S5", "M3", "x")), (name) => {
      const parsed = parseSegment(name);
      if (parsed === null) return;
      assert.ok(Number.isInteger(parsed.number) && parsed.number >= 0);
      assert.ok([0, 1, 2, 3].includes(parsed.multiplier));
    }),
    RUNS
  );
});

test("heat levels only name real beds and add up to the hits", () => {
  const key = fc.oneof(
    fc.constantFrom("BULL", "25", "MISS", "X9", "T21", "__proto__", "constructor"),
    fc.tuple(fc.constantFrom("S", "D", "T"), fc.integer({ min: 0, max: 25 })).map(([bed, n]) => `${bed}${n}`),
    fc.string()
  );
  const hits = fc.dictionary(key, fc.oneof(fc.integer({ min: -3, max: 50 }), fc.string(), fc.constant(null)));
  fc.assert(
    fc.property(hits, fc.constantFrom("beds", "numbers"), (value, mode) => {
      const levels = heatLevels(value, mode);
      for (const [bed, count] of levels) {
        assert.notEqual(bedPath(bed), null, bed);
        assert.ok(Number.isInteger(count) && count > 0);
      }
      const max = Math.max(0, ...levels.values());
      for (const count of levels.values()) {
        const ratio = heatRatio(count, max);
        assert.ok(ratio >= 0 && ratio <= 1);
      }
    }),
    RUNS
  );
});

test("the most hit beds are sorted, limited and never misses", () => {
  fc.assert(
    fc.property(fc.dictionary(fc.string(), fc.integer({ min: -2, max: 30 })), fc.integer({ min: 0, max: 8 }), (hits, limit) => {
      const top = topHits(hits, limit);
      assert.ok(top.length <= limit);
      for (let index = 1; index < top.length; index += 1) assert.ok(top[index - 1][1] >= top[index][1]);
      assert.ok(top.every(([name, count]) => name !== "MISS" && count > 0));
    }),
    RUNS
  );
});

test("higher visits never fall into a lower bucket", () => {
  const order = ["low", "good", "ton", "high", "max"];
  fc.assert(
    fc.property(fc.integer({ min: 0, max: 200 }), fc.integer({ min: 0, max: 200 }), (a, b) => {
      const [low, high] = a <= b ? [a, b] : [b, a];
      assert.ok(order.indexOf(visitBucket(low)) <= order.indexOf(visitBucket(high)));
    }),
    RUNS
  );
});

test("any recorder history is read without errors", () => {
  fc.assert(
    fc.property(fc.anything(), fc.integer({ min: 0, max: 2e12 }), (rows, since) => {
      for (const visit of visitsFromHistory(rows, since)) {
        assert.ok(Number.isFinite(visit.score) && visit.time >= since);
        assert.ok(Array.isArray(visit.segments));
      }
    }),
    RUNS
  );
});

test("session and visit lists from hostile attributes stay finite and textual", () => {
  fc.assert(
    fc.property(fc.anything(), fc.anything(), (visits, sessions) => {
      for (const visit of recentVisits(visits)) {
        assert.ok(Number.isInteger(visit.score) && visit.score >= 0);
        assert.ok(visit.segments.every((segment) => typeof segment === "string"));
      }
      for (const session of pastSessions(sessions)) {
        assert.ok(Number.isFinite(session.ended) && session.darts > 0);
        for (const key of ["minutes", "average", "best"]) {
          assert.ok(session[key] === null || Number.isFinite(session[key]));
        }
      }
    }),
    RUNS
  );
});
