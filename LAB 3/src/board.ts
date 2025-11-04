/* Copyright (c) 2021-25 MIT 6.102/6.031 course staff, all rights reserved.
 * Redistribution of original or derived work requires permission of course staff.
 */

import assert from "node:assert";
import fs from "node:fs";

/**
 * A mutable Memory Scramble game board that supports concurrent players.
 *
 * The board consists of a grid of spaces that may contain cards.
 * Cards can be face-down, face-up, or removed from the board.
 * Players can control cards and attempt to match pairs.
 */

type CardState = "none" | "face-up" | "face-down";

type Spot = {
  card: string | undefined;
  state: CardState;
  controller: string | undefined;
};

/** Player state tracking */
type PlayerState = {
  firstCard: { row: number; col: number } | undefined;
  previousCards: Array<{ row: number; col: number }>;
};

export class Board {
  private readonly rows: number;
  private readonly cols: number;
  private readonly grid: Spot[][];
  private readonly players: Map<string, PlayerState>;

  // Abstraction function:
  //   AF(rows, cols, grid, players) = a Memory Scramble game board with dimensions rows x cols
  //     where grid[r][c] represents the spot at position (r, c):
  //       - grid[r][c].card is the card string at that position, or undefined if no card
  //       - grid[r][c].state is 'none' if no card, 'face-down' if card is face down, 'face-up' if face up
  //       - grid[r][c].controller is the player ID controlling this card, or undefined if not controlled
  //     and players maps each player ID to their game state:
  //       - firstCard is the position of the first card they're trying to match, or undefined
  //       - previousCards are the cards from their last unsuccessful match attempt
  //
  // Representation invariant:
  //   - rows > 0, cols > 0
  //   - grid.length === rows
  //   - for all r in [0, rows): grid[r].length === cols
  //   - for all spots in grid:
  //       - if spot.state === 'none', then spot.card === undefined and spot.controller === undefined
  //       - if spot.state === 'face-down', then spot.card !== undefined and spot.controller === undefined
  //       - if spot.state === 'face-up', then spot.card !== undefined
  //       - if spot.controller !== undefined, then spot.state === 'face-up'
  //   - for all player states:
  //       - if firstCard is defined, then grid[firstCard.row][firstCard.col].controller === playerID
  //       - all positions in previousCards refer to valid grid positions
  //   - no two players can control the same card
  //
  // Safety from rep exposure:
  //   - all fields are private and readonly (except grid contents which are mutable)
  //   - rows, cols are immutable numbers
  //   - grid is never returned directly; only defensive copies or string representations
  //   - players Map is never returned directly
  //   - all methods return strings or promises, never mutable rep components

  /**
   * Create a new Memory Scramble board.
   *
   * @param rows number of rows in the board, must be > 0
   * @param cols number of columns in the board, must be > 0
   * @param cards array of card strings to place on the board, must have exactly rows * cols elements
   */
  private constructor(rows: number, cols: number, cards: string[]) {
    this.rows = rows;
    this.cols = cols;
    this.players = new Map();

    // Initialize grid with face-down cards
    this.grid = [];
    let cardIndex = 0;
    for (let r = 0; r < rows; r++) {
      this.grid[r] = [];
      const row = this.grid[r];
      assert(row !== undefined);
      for (let c = 0; c < cols; c++) {
        row[c] = {
          card: cards[cardIndex++],
          state: "face-down",
          controller: undefined,
        };
      }
    }

    this.checkRep();
  }

  /**
   * Check the representation invariant.
   */
  private checkRep(): void {
    assert(this.rows > 0, "rows must be positive");
    assert(this.cols > 0, "cols must be positive");
    assert(
      this.grid.length === this.rows,
      "grid must have correct number of rows"
    );

    const controlledCards = new Map<string, string>(); // position -> playerID

    for (let r = 0; r < this.rows; r++) {
      const row = this.grid[r];
      assert(row !== undefined, `row ${r} must exist`);
      assert(
        row.length === this.cols,
        `row ${r} must have correct number of columns`
      );

      for (let c = 0; c < this.cols; c++) {
        const spot = row[c];
        assert(spot !== undefined, `spot at (${r},${c}) must exist`);

        if (spot.state === "none") {
          assert(
            spot.card === undefined,
            `empty spot at (${r},${c}) should have no card`
          );
          assert(
            spot.controller === undefined,
            `empty spot at (${r},${c}) should have no controller`
          );
        } else if (spot.state === "face-down") {
          assert(
            spot.card !== undefined,
            `face-down spot at (${r},${c}) must have a card`
          );
          assert(
            spot.controller === undefined,
            `face-down spot at (${r},${c}) should have no controller`
          );
        } else {
          // face-up
          assert(
            spot.card !== undefined,
            `face-up spot at (${r},${c}) must have a card`
          );
        }

        if (spot.controller !== undefined) {
          assert(
            spot.state === "face-up",
            `controlled spot at (${r},${c}) must be face-up`
          );
          const key = `${r},${c}`;
          assert(
            !controlledCards.has(key),
            `spot at (${r},${c}) controlled by multiple players`
          );
          controlledCards.set(key, spot.controller);
        }
      }
    }
  }

  /**
   * @returns a string representation of this board showing the grid state
   */
  public toString(): string {
    let result = `Board ${this.rows}x${this.cols}\n`;
    for (let r = 0; r < this.rows; r++) {
      const row = this.grid[r];
      assert(row !== undefined);
      for (let c = 0; c < this.cols; c++) {
        const spot = row[c];
        assert(spot !== undefined);
        if (spot.state === "none") {
          result += "[    ] ";
        } else if (spot.state === "face-down") {
          result += "[????] ";
        } else {
          const ctrl = spot.controller
            ? `*${spot.controller.substring(0, 1)}*`
            : "   ";
          result += `[${spot.card?.substring(0, 2).padEnd(2)}${ctrl}] `;
        }
      }
      result += "\n";
    }
    return result;
  }

  /**
   * Make a new board by parsing a file.
   *
   * PS4 instructions: the specification of this method may not be changed.
   *
   * @param filename path to game board file
   * @returns a new board with the size and cards from the file
   * @throws Error if the file cannot be read or is not a valid game board
   */
  public static async parseFromFile(filename: string): Promise<Board> {
    const content = await fs.promises.readFile(filename, { encoding: "utf-8" });
    const lines = content.split(/\r?\n/);

    // Parse first line: ROWxCOLUMN
    if (lines.length < 1) {
      throw new Error("empty file");
    }

    const dimensionMatch = lines[0]?.match(/^(\d+)x(\d+)$/);
    if (!dimensionMatch) {
      throw new Error("invalid board dimensions format");
    }

    const rows = parseInt(dimensionMatch[1] ?? "0");
    const cols = parseInt(dimensionMatch[2] ?? "0");

    if (rows <= 0 || cols <= 0) {
      throw new Error("board dimensions must be positive");
    }

    const expectedCards = rows * cols;

    // Parse card lines
    const cards: string[] = [];
    for (let i = 1; i <= expectedCards; i++) {
      const line = lines[i];
      if (line === undefined || line === "") {
        throw new Error(`missing card at line ${i + 1}`);
      }

      // Card must be non-empty and contain no whitespace or newlines
      if (!/^[^\s\r\n]+$/.test(line)) {
        throw new Error(`invalid card format at line ${i + 1}`);
      }

      cards.push(line);
    }

    if (cards.length !== expectedCards) {
      throw new Error(
        `expected ${expectedCards} cards but found ${cards.length}`
      );
    }

    return new Board(rows, cols, cards);
  }
}
