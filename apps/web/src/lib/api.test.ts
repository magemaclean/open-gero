import { describe, expect, it } from "vitest";
import { parseSuccessBody } from "../api";

describe("parseSuccessBody", () => {
  it("does not parse JSON on 204 or empty bodies", () => {
    expect(parseSuccessBody(204, "application/json", "")).toBeUndefined();
    expect(parseSuccessBody(200, "application/json", "")).toBeUndefined();
    expect(parseSuccessBody(200, "application/json", "   ")).toBeUndefined();
  });

  it("parses JSON payloads", () => {
    expect(parseSuccessBody(200, "application/json; charset=utf-8", '{"ok":true}')).toEqual({ ok: true });
  });
});
