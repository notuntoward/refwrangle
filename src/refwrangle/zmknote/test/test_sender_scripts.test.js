/**
 * Vitest regression tests for the Zotero → Obsidian sender scripts.
 *
 * Run with:  npm test   (or: npx vitest run)
 *
 * Strategy
 * --------
 * The sender scripts are Zotero action scripts — plain JS files with no
 * import/export syntax.  They rely on Zotero-specific globals (Zotero,
 * item, items) and are not ES modules.
 *
 * To test pure functions from those scripts without running the full
 * Zotero environment, we:
 *   1. Read the source file.
 *   2. Extract just the function definition(s) under test using a regex.
 *   3. eval() the extracted source in an isolated scope.
 *   4. Call the resulting function directly.
 *
 * This lets us verify the exact production logic without copying code or
 * introducing an import mechanism the scripts don't support.
 */

import { readFileSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { describe, it, expect, beforeAll } from 'vitest'

// ---------------------------------------------------------------------------
// Resolve paths relative to the test file
// ---------------------------------------------------------------------------
const __filename = fileURLToPath(import.meta.url)
const __dirname  = dirname(__filename)
const SRC_DIR    = resolve(__dirname, '..')

// ---------------------------------------------------------------------------
// Helper: extract a named function from a JS source string and eval it.
// Returns the function object so tests can call it directly.
// ---------------------------------------------------------------------------
function extractFunction(source, fnName) {
  // Match `function fnName(…) { … }` (handles multi-line bodies via a
  // simple brace-depth counter rather than a fragile regex).
  const startPattern = new RegExp(`function\\s+${fnName}\\s*\\(`)
  const startIdx = source.search(startPattern)
  if (startIdx === -1) throw new Error(`Function '${fnName}' not found in source`)

  let depth = 0
  let inFunction = false
  let endIdx = startIdx

  for (let i = startIdx; i < source.length; i++) {
    if (source[i] === '{') { depth++; inFunction = true }
    if (source[i] === '}') { depth-- }
    if (inFunction && depth === 0) { endIdx = i + 1; break }
  }

  const fnSource = source.slice(startIdx, endIdx)
  // Evaluate in a clean scope and return the function
  // eslint-disable-next-line no-new-func
  const wrapper = new Function(`${fnSource}; return ${fnName};`)
  return wrapper()
}

// ---------------------------------------------------------------------------
// Load source once per suite
// ---------------------------------------------------------------------------
let newSenderSource
let validateCitationKey
let localISOString

beforeAll(() => {
  newSenderSource = readFileSync(resolve(SRC_DIR, 'new_obsidian_note_sender.js'), 'utf8')
  validateCitationKey = extractFunction(newSenderSource, 'validateCitationKey')
  localISOString = extractFunction(newSenderSource, 'localISOString')
})

// ===========================================================================
// validateCitationKey — new_obsidian_note_sender.js
// ===========================================================================

describe('validateCitationKey', () => {

  // ---- Valid inputs --------------------------------------------------------

  it('accepts a normal citation key', () => {
    const result = validateCitationKey('Smith2024someTitle')
    expect(result.valid).toBe(true)
    expect(result.reason).toBeNull()
  })

  it('accepts a citation key with hyphens and underscores', () => {
    expect(validateCitationKey('smith-2024_title').valid).toBe(true)
  })

  it('accepts a single-character key', () => {
    expect(validateCitationKey('A').valid).toBe(true)
  })

  it('accepts a Unicode key (non-ASCII)', () => {
    // Non-ASCII characters are allowed — they are not in the Windows-forbidden set
    expect(validateCitationKey('Müller2024').valid).toBe(true)
  })

  it('accepts a key exactly 252 characters long (max before .md = 255)', () => {
    const key = 'A'.repeat(252)
    expect(validateCitationKey(key).valid).toBe(true)
  })

  // ---- Invalid: empty / wrong type ----------------------------------------

  it('rejects an empty string', () => {
    const result = validateCitationKey('')
    expect(result.valid).toBe(false)
  })

  it('rejects a whitespace-only string', () => {
    expect(validateCitationKey('   ').valid).toBe(false)
  })

  it('rejects null', () => {
    expect(validateCitationKey(null).valid).toBe(false)
  })

  it('rejects undefined', () => {
    expect(validateCitationKey(undefined).valid).toBe(false)
  })

  it('rejects a number', () => {
    expect(validateCitationKey(42).valid).toBe(false)
  })

  // ---- Invalid: Windows-forbidden characters -------------------------------

  it.each(['<', '>', ':', '"', '/', '\\', '|', '?', '*'])(
    'rejects a key containing "%s"', (char) => {
      const result = validateCitationKey(`Smith${char}2024`)
      expect(result.valid).toBe(false)
      expect(result.reason).toContain('invalid character')
    }
  )

  it('error message names the offending printable character', () => {
    const result = validateCitationKey('Smith:2024')
    expect(result.valid).toBe(false)
    expect(result.reason).toContain("':'")
  })

  it('error message uses CTRL-XX for control characters', () => {
    // NUL (0x00) should appear as CTRL-00
    const result = validateCitationKey('Smith\x002024')
    expect(result.valid).toBe(false)
    expect(result.reason).toMatch(/CTRL-00/i)
  })

  it('error message uses TAB label for tab character', () => {
    const result = validateCitationKey('Smith\t2024')
    expect(result.valid).toBe(false)
    expect(result.reason).toContain('TAB')
  })

  it('error message uses NEWLINE label for newline character', () => {
    const result = validateCitationKey('Smith\n2024')
    expect(result.valid).toBe(false)
    expect(result.reason).toContain('NEWLINE')
  })

  it('error message uses CR label for carriage return', () => {
    const result = validateCitationKey('Smith\r2024')
    expect(result.valid).toBe(false)
    expect(result.reason).toContain('CR')
  })

  // ---- Invalid: Windows reserved names ------------------------------------

  it.each(['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM9', 'LPT1', 'LPT9'])(
    'rejects reserved name "%s"', (name) => {
      expect(validateCitationKey(name).valid).toBe(false)
    }
  )

  it('rejects reserved names case-insensitively (con)', () => {
    expect(validateCitationKey('con').valid).toBe(false)
  })

  // ---- Invalid: leading / trailing whitespace / period --------------------

  it('rejects a key with leading spaces', () => {
    expect(validateCitationKey(' Smith2024').valid).toBe(false)
  })

  it('rejects a key with trailing spaces', () => {
    expect(validateCitationKey('Smith2024 ').valid).toBe(false)
  })

  it('rejects a key ending in a period', () => {
    expect(validateCitationKey('Smith2024.').valid).toBe(false)
  })

  // ---- Invalid: too long --------------------------------------------------

  it('rejects a key longer than 252 characters', () => {
    const key = 'A'.repeat(253)  // 253 + 3 ('.md') = 256 > 255
    const result = validateCitationKey(key)
    expect(result.valid).toBe(false)
    expect(result.reason).toMatch(/too long/i)
  })

  // ---- Regression: NULL branch must NOT hardcode 'NULL' for \x00 ----------
  // (Fixed: replaced standalone '\x00' → 'NULL' with CTRL-XX fallback)

  it('does NOT label NUL character as the literal word "NULL" (old behaviour)', () => {
    // After the fix, \x00 should be labelled CTRL-00, not NULL
    const result = validateCitationKey('\x00')
    expect(result.valid).toBe(false)
    // Must use the new CTRL-XX style
    expect(result.reason).toMatch(/CTRL-00/i)
    // Must NOT use the old hardcoded label
    expect(result.reason).not.toContain('NULL')
  })
})

// ===========================================================================
// localISOString — new_obsidian_note_sender.js
// ===========================================================================

describe('localISOString', () => {
  // Helper to compute the expected local-ISO string using the same source of
  // truth as the implementation (the Date object's local getters and offset).
  function expectedLocalISOString(date) {
    const pad = n => String(n).padStart(2, '0')
    const offset = -date.getTimezoneOffset()
    const sign = offset >= 0 ? '+' : '-'
    const abs = Math.abs(offset)
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
           `T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}` +
           `${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`
  }

  it('formats a date in local time with the correct offset', () => {
    const date = new Date('2024-06-15T10:30:45-07:00')
    expect(localISOString(date)).toBe(expectedLocalISOString(date))
  })

  it('pads single-digit month/day/hour/minute/second', () => {
    const date = new Date(2024, 0, 5, 8, 5, 9)
    expect(localISOString(date)).toBe(expectedLocalISOString(date))
  })

  it('defaults to the current date when called with no arguments', () => {
    const before = Date.now()
    const result = localISOString()
    const after = Date.now()
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$/)
    const parsed = Date.parse(result)
    // Allow one second of slack because the result is truncated to whole seconds.
    expect(parsed).toBeGreaterThanOrEqual(before - 1000)
    expect(parsed).toBeLessThanOrEqual(after)
  })

  it('formats a date that is east of UTC relative to the local offset', () => {
    const date = new Date('2024-12-25T15:00:00+09:00')
    expect(localISOString(date)).toBe(expectedLocalISOString(date))
  })

  it('formats a date that is west of UTC relative to the local offset', () => {
    const date = new Date('2024-12-25T15:00:00-03:00')
    expect(localISOString(date)).toBe(expectedLocalISOString(date))
  })
})

// ===========================================================================
// Structural checks — verify functions still exist in the source files
// and have not been accidentally deleted or renamed.
// ===========================================================================

describe('source structure: new_obsidian_note_sender.js', () => {

  it('contains validateCitationKey function definition', () => {
    expect(newSenderSource).toMatch(/function\s+validateCitationKey\s*\(/)
  })

  it('contains sendToWebhook function definition', () => {
    expect(newSenderSource).toMatch(/function\s+sendToWebhook\s*\(/)
  })

  it('uses ZoteroWebhookLock to prevent duplicate processing', () => {
    expect(newSenderSource).toContain('ZoteroWebhookLock')
    expect(newSenderSource).toContain('inProgress')
  })

  it('has the timedOut guard in sendToWebhook (race condition fix)', () => {
    // Regression: stale webhook responses were processed after timeout fired.
    // Fix: timedOut flag set in the timeout callback and checked in .then()/.catch()
    expect(newSenderSource).toContain('timedOut')
  })

  it('validates citekey before sending (invalid citekey popup)', () => {
    expect(newSenderSource).toContain('validateCitationKey(citekey)')
  })

  it('uses CTRL-XX hex style for control chars (not the old hardcoded NULL)', () => {
    // Regression: old code had `if (c === '\x00') return 'NULL'` as a standalone branch.
    // Fix: replaced with generic CTRL-XX handler.
    // Verify the old branch is absent.
    expect(newSenderSource).not.toMatch(/===\s*['"`]\\x00['"`]\s*\)\s*return\s*['"`]NULL['"`]/)
    // And the new pattern is present
    expect(newSenderSource).toContain('CTRL-')
  })
})

describe('source structure: open_obsidian_note_sender.js', () => {

  let openSenderSource

  beforeAll(() => {
    openSenderSource = readFileSync(resolve(SRC_DIR, 'open_obsidian_note_sender.js'), 'utf8')
  })

  it('contains sendToWebhook function', () => {
    expect(openSenderSource).toMatch(/function\s+sendToWebhook\s*\(/)
  })

  it('uses ZoteroWebhookLock', () => {
    expect(openSenderSource).toContain('ZoteroWebhookLock')
  })

  it('sends citekeys as an array (not itemData objects)', () => {
    // open_obsidian_note_sender.js pushes plain citekey strings, not full item objects
    expect(openSenderSource).toContain('itemDataArray.push(citekey)')
  })

  it('uses SENDER_ID_OPEN_OBSIDIAN_NOTE as sender_id', () => {
    expect(openSenderSource).toContain("SENDER_ID_OPEN_OBSIDIAN_NOTE")
    expect(openSenderSource).toContain("'open_obsidian_note'")
  })

  it('has startup debug logging (for diagnosing silent failures)', () => {
    expect(openSenderSource).toContain('OPEN_OBSIDIAN_NOTE_SENDER SCRIPT STARTING')
  })
})
