import { describe, expect, it } from "vitest";
import { PAGE_SIZE, formatMetric, jobSocketUrl, moleculeQuery } from "./query";

describe("moleculeQuery", () => {
  it("always sends limit and offset", () => {
    const q = moleculeQuery({});
    expect(q.get("limit")).toBe(String(PAGE_SIZE));
    expect(q.get("offset")).toBe("0");
  });

  it("includes extra filters used by the library builder", () => {
    const q = moleculeQuery({
      q: "aspirin",
      mwMin: "100",
      mwMax: "500",
      tpsaMax: "140",
      logpMax: "5",
      lipinski: true,
      veber: true,
      offset: 50,
    });
    expect(q.get("q")).toBe("aspirin");
    expect(q.get("mw_min")).toBe("100");
    expect(q.get("mw_max")).toBe("500");
    expect(q.get("tpsa_max")).toBe("140");
    expect(q.get("logp_max")).toBe("5");
    expect(q.get("lipinski")).toBe("true");
    expect(q.get("veber")).toBe("true");
    expect(q.get("offset")).toBe("50");
  });

  it("marks the deleted-library view", () => {
    expect(moleculeQuery({ deleted: true }).get("deleted")).toBe("true");
  });
});

describe("jobSocketUrl", () => {
  it("uses ws and the token query on http hosts", () => {
    expect(jobSocketUrl("job-1", "abc+def", { protocol: "http:", host: "localhost:8080" })).toBe(
      "ws://localhost:8080/api/ws/jobs/job-1?token=abc%2Bdef",
    );
  });

  it("uses wss on https and omits the query when unsigned", () => {
    expect(jobSocketUrl("job-1", null, { protocol: "https:", host: "lab.example" })).toBe(
      "wss://lab.example/api/ws/jobs/job-1",
    );
  });
});

describe("formatMetric", () => {
  it("shows an em dash instead of 0.00 for missing QED", () => {
    expect(formatMetric(null)).toBe("—");
    expect(formatMetric(undefined)).toBe("—");
    expect(formatMetric(Number.NaN)).toBe("—");
  });

  it("keeps two decimals for QED-scale values", () => {
    expect(formatMetric(0.55)).toBe("0.55");
    expect(formatMetric(180.12)).toBe("180.1");
  });
});
