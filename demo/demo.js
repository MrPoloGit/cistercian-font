// Cistercian numeral font demo: a number converter, a letter converter, and
// a 0-9999 chart. Addresses the font's precomposed glyphs directly (one
// codepoint per number, Supplementary PUA-A starting at U+F0000), so this
// works whether or not the browser applies ss01/ss02 to the fallback font.

const PRECOMPOSED_BASE = 0xf0000;

// Mirrors spec/letters.json (mapping_mode: "shared"): A-Z map to 1-26, and
// lowercase shares the same numeral as uppercase.
const LETTER_VALUES = Object.fromEntries(
  "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").map((letter, index) => [letter, index + 1]),
);

function numeralChar(number) {
  if (number < 0 || number > 9999) {
    throw new RangeError(`${number} is outside the 0-9999 range this font supports`);
  }
  return String.fromCodePoint(PRECOMPOSED_BASE + number);
}

function letterValue(letter) {
  const value = LETTER_VALUES[letter.toUpperCase()];
  return value === undefined ? null : value;
}

function setUpNumberConverter() {
  const input = document.getElementById("number-input");
  const output = document.getElementById("number-output");

  function render() {
    const number = Number(input.value);
    if (!Number.isInteger(number) || number < 0 || number > 9999) {
      output.textContent = "";
      return;
    }
    output.textContent = numeralChar(number);
  }

  input.addEventListener("input", render);
  render();
}

function setUpLetterConverter() {
  const input = document.getElementById("letter-input");
  const output = document.getElementById("letter-output");

  function render() {
    output.innerHTML = "";
    for (const letter of input.value) {
      const value = letterValue(letter);
      if (value === null) {
        continue;
      }
      const cell = document.createElement("div");
      cell.className = "letter-cell";

      const numeral = document.createElement("span");
      numeral.className = "numeral";
      numeral.textContent = numeralChar(value);

      const label = document.createElement("span");
      label.className = "letter-label";
      label.textContent = letter.toUpperCase();

      cell.append(numeral, label);
      output.append(cell);
    }
  }

  input.addEventListener("input", render);
  render();
}

function setUpChart() {
  const grid = document.getElementById("chart-grid");
  const pageInput = document.getElementById("chart-page");
  const prevButton = document.getElementById("chart-prev");
  const nextButton = document.getElementById("chart-next");
  const pageSize = 100;
  const pageCount = 10000 / pageSize;

  function render() {
    const page = Math.min(Math.max(0, Number(pageInput.value) || 0), pageCount - 1);
    pageInput.value = String(page);
    grid.innerHTML = "";
    const start = page * pageSize;
    for (let number = start; number < start + pageSize; number += 1) {
      const cell = document.createElement("div");
      cell.className = "chart-cell";

      const numeral = document.createElement("span");
      numeral.className = "numeral";
      numeral.textContent = numeralChar(number);

      const label = document.createElement("span");
      label.className = "number-label";
      label.textContent = String(number);

      cell.append(numeral, label);
      grid.append(cell);
    }
  }

  prevButton.addEventListener("click", () => {
    pageInput.value = String(Number(pageInput.value) - 1);
    render();
  });
  nextButton.addEventListener("click", () => {
    pageInput.value = String(Number(pageInput.value) + 1);
    render();
  });
  pageInput.addEventListener("input", render);
  render();
}

setUpNumberConverter();
setUpLetterConverter();
setUpChart();
