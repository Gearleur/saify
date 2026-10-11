import { describe, expect, it } from "vitest";
import { checkFile, sourceOf, MAX_SIZE } from "./files";

describe("sourceOf", () => {
  it("reconnaît la source sans tenir compte de la casse, comme le back", () => {
    expect(sourceOf("positions_internes.csv")).toBe("PMS");
    expect(sourceOf("Depositaire_a_20260925.xlsx")).toBe("A");
    expect(sourceOf("DEPOSITAIRE_C_20260925.XML")).toBe("C");
  });

  it("refuse un nom inconnu", () => {
    expect(sourceOf("releve_inconnu.csv")).toBeNull();
    expect(sourceOf("depositaire_D_20260925.txt")).toBeNull();
  });
});

describe("checkFile", () => {
  const file = (name: string, size = 10) => new File([new Uint8Array(size)], name);

  it("accepte un fichier attendu", () => {
    expect(checkFile(file("depositaire_B_20260925.txt"))).toBeNull();
  });

  it("explique chaque refus", () => {
    expect(checkFile(file("depositaire_B_20260925.pdf"))).toMatch(/Extension/);
    expect(checkFile(file("notes.csv"))).toMatch(/Nom non reconnu/);
    expect(checkFile(file("positions_internes.csv", MAX_SIZE + 1))).toMatch(/5 Mo/);
  });
});
