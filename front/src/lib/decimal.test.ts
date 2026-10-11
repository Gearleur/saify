import { describe, expect, it } from "vitest";
import { compareDecimal, formatDecimal, isDecimal, isNegative, isZero } from "./decimal";

const THIN_SPACE = "\u202f";

describe("formatDecimal", () => {
  it("groupe les milliers par une espace fine et garde la virgule décimale", () => {
    expect(formatDecimal("250000")).toBe(`250${THIN_SPACE}000`);
    expect(formatDecimal("724836.00")).toBe(`724${THIN_SPACE}836,00`);
  });

  it("écrit un vrai signe moins, et + seulement si demandé", () => {
    expect(formatDecimal("-30000")).toBe(`\u221230${THIN_SPACE}000`);
    expect(formatDecimal("25000", true)).toBe(`+25${THIN_SPACE}000`);
    expect(formatDecimal("0", true)).toBe("0");
  });

  it("n'écrit jamais −0", () => {
    expect(formatDecimal("-0.00")).toBe("0,00");
    expect(isNegative("-0")).toBe(false);
  });

  it("garde tous les chiffres d'un grand nombre (aucun passage par un flottant)", () => {
    expect(formatDecimal("12345678901234567.89")).toBe(
      `12${THIN_SPACE}345${THIN_SPACE}678${THIN_SPACE}901${THIN_SPACE}234${THIN_SPACE}567,89`,
    );
  });

  it("rend une valeur absente ou illisible sans l'inventer", () => {
    expect(formatDecimal(null)).toBe("—");
    expect(formatDecimal("")).toBe("—");
    expect(formatDecimal("abc")).toBe("abc");
    expect(isDecimal("1e5")).toBe(false);
  });
});

describe("compareDecimal", () => {
  it("trie exactement, négatifs d'abord, valeurs absentes en dernier", () => {
    const values = ["10", "-30000", "9.99", null, "0.1", "-2", "100"];
    expect([...values].sort(compareDecimal)).toEqual([
      "-30000",
      "-2",
      "0.1",
      "9.99",
      "10",
      "100",
      null,
    ]);
  });

  it("compare des décimales de longueurs différentes", () => {
    expect(compareDecimal("1.5", "1.50")).toBe(0);
    expect(compareDecimal("0.1", "0.09")).toBeGreaterThan(0);
  });

  it("isZero accepte toutes les écritures de zéro", () => {
    expect(["0", "0.00", "-0", "000"].every(isZero)).toBe(true);
    expect(isZero("0.01")).toBe(false);
  });
});
