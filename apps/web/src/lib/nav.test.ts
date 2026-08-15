import { describe, expect, it } from "vitest";
import { crumbsFor, projectPageLabel } from "./nav";

describe("projectPageLabel", () => {
  it("is null on the project library home", () => {
    expect(projectPageLabel("/projects/abc", "abc")).toBeNull();
    expect(projectPageLabel("/projects/abc/", "abc")).toBeNull();
  });

  it("names nested project pages", () => {
    expect(projectPageLabel("/projects/abc/editor", "abc")).toBe("Draw / add");
    expect(projectPageLabel("/projects/abc/search", "abc")).toBe("Search");
    expect(projectPageLabel("/projects/abc/jobs", "abc")).toBe("Jobs");
    expect(projectPageLabel("/projects/abc/jobs/job-1", "abc")).toBe("Job");
    expect(projectPageLabel("/projects/abc/molecules/m1", "abc")).toBe("Molecule");
  });
});

describe("crumbsFor", () => {
  it("always starts at Projects", () => {
    expect(crumbsFor("/", null)[0]).toEqual({ label: "Projects", to: "/" });
  });

  it("links the project when a nested page is open", () => {
    const crumbs = crumbsFor("/projects/p1/search", { id: "p1", name: "Senolytic shortlist" });
    expect(crumbs).toEqual([
      { label: "Projects", to: "/" },
      { label: "Senolytic shortlist", to: "/projects/p1" },
      { label: "Search" },
    ]);
  });
});
