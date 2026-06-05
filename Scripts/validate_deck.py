#!/usr/bin/env python3
"""Static validation for the Chromatyx nanDECK deck project.

Checks the deck script (*.nde) and its linked spreadsheet for problems that
would otherwise only surface during a render (or worse, on paper): unknown
directives, unbalanced VISUAL blocks, dangling or non-portable file
references, malformed colors and expressions, label/column mismatches and
inconsistent card data.

Usage: validate_deck.py [path/to/Game.nde]

Exit code 0 = no errors (warnings allowed), 1 = at least one error.
Findings are emitted as GitHub Actions annotations when running in CI.

Only the Python standard library is used.
"""
from __future__ import annotations

import os
import re
import sys
import zipfile
from dataclasses import dataclass
from xml.etree import ElementTree as ET

_XLSX_NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
_RELS_NS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

# Directives from the nanDECK reference manual; unknown ones yield a warning
# (not an error) so a manual/validator version skew never breaks the build.
KNOWN_DIRECTIVES = frozenset("""
    BASERANGE BATCH BEZIER BLEED BORDER BUTTON CANVAS CARDS CARDSIZE CASE
    CHROMAKEY CIRCLE COLORCHANGE COLORS COMMENT COPY CORRECTION COUNTERS
    CROPMARK DEBUG DICE DISPLAY DPI DRAW DUPLEX EDGE ELLIPSE ELSE ELSEIF END
    ENDIF ENDLINK ENDSECTION ENDSELECT ENDVISUAL FILL FLAGS FOLD FONT
    FONTALIAS FONTCHANGE FONTRANGE FOOTER FOR FRAME GAP GRID HEXGRID
    HTMLBORDER HTMLFILE HTMLFONT HTMLIMAGE HTMLKEY HTMLMARGINS HTMLTEXT ICON
    ICONS IF IMAGE IMAGEENC IMAGEFILTER IMAGESIZE INCLUDE INPUTCHOICE
    INPUTLIST INPUTNUMBER INPUTTEXT LABEL LABELRANGE LABELSUB LAYER LIMIT
    LINE LINERECT LINK LINKCOLOR LINKENC LINKFILTER LINKICONS LINKMULTI
    LINKNETWORK LINKRANDOM LINKSEP LINKSPLIT LINKTRIM LOG LOOP MARGINS MOSAIC
    NEXT ORIGIN OVAL PAGE PAGEFONT PAGEIMAGE PAGETEXT PATTERN POLYGON PRINT
    RECTANGLE RENAME RHOMBUS ROUNDRECT SAVE SAVEPAGES SAVEPDF SECTION SELECT
    SEQUENCE STAR STORE TABLE TAG TEXT TOKEN TRACK TRIANGLE UNIT VISUAL ZOOM
""".split())

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tif', '.tiff')


@dataclass
class Finding:
  level: str  # 'error' | 'warning'
  file: str
  line: int  # 1-based, 0 = whole file
  message: str

  def __str__(self):
    location = f"{self.file}:{self.line}" if self.line else self.file
    return f"{self.level.upper()}: {location}: {self.message}"

  def as_annotation(self):
    location = f"file={self.file},line={self.line}" if self.line else f"file={self.file}"
    return f"::{self.level} {location}::{self.message}"


@dataclass
class Directive:
  line: int
  name: str  # uppercase
  value: str


@dataclass
class DeckScript:
  path: str
  directives: list  # of Directive
  labels: dict  # lowercase label name -> (line, value)

  def all(self, name):
    return [d for d in self.directives if d.name == name]

  def first(self, name):
    matches = self.all(name)
    return matches[0] if matches else None


def parse_script(path):
  """Reads a nanDECK script (cp1252, the format's native encoding)."""
  with open(path, 'r', encoding='cp1252') as f:
    raw_lines = f.read().splitlines()

  directives, labels = [], {}
  for number, raw in enumerate(raw_lines, start=1):
    line = raw.strip()
    if not line or line.startswith(';'):
      continue
    label_match = re.match(r'^\[([^\]\[=]+)\]=(.*)$', line)
    if label_match:
      labels[label_match.group(1).lower()] = (number, label_match.group(2))
      continue
    directive_match = re.match(r'^([A-Za-z][A-Za-z0-9]*)=(.*)$', line)
    if directive_match:
      directives.append(Directive(number, directive_match.group(1).upper(), directive_match.group(2)))
      continue
    directives.append(Directive(number, line.upper(), ''))  # bare keyword such as ENDVISUAL

  return DeckScript(path, directives, labels)


def split_fields(value):
  """Splits a directive value on commas, honoring double quotes."""
  fields, current, quoted = [], '', False
  for char in value:
    if char == '"':
      quoted = not quoted
      current += char
    elif char == ',' and not quoted:
      fields.append(current.strip())
      current = ''
    else:
      current += char
  fields.append(current.strip())
  return fields


def unquote(text):
  text = text.strip()
  return text[1:-1] if len(text) >= 2 and text[0] == '"' and text[-1] == '"' else text


def exists_with_exact_case(base_dir, relative):
  """True if `relative` exists below `base_dir` with byte-exact casing.

  Windows resolves `icons\\block.png` for `Icons\\Block.png`; a Linux CI
  runner or print service does not, so casing mismatches are treated as
  missing files.
  """
  current = base_dir
  for part in re.split(r'[\\/]+', relative):
    if part in ('', '.'):
      continue
    if not os.path.isdir(current) or part not in os.listdir(current):
      return False
    current = os.path.join(current, part)
  return True


def is_absolute_reference(path):
  return bool(re.match(r'^([A-Za-z]:|\\\\|//|[\\/])', path))


def load_xlsx(path, sheet_name=None):
  """Returns (header, rows) of a worksheet; cells are strings keyed by column letter."""
  archive = zipfile.ZipFile(path)
  workbook = ET.fromstring(archive.read('xl/workbook.xml'))
  relationships = {
      rel.get('Id'): rel.get('Target')
      for rel in ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
  }
  sheet_file = None
  for sheet in workbook.iter(_XLSX_NS + 'sheet'):
    if sheet_name is None or sheet.get('name').lower() == sheet_name.lower():
      target = relationships[sheet.get(_RELS_NS + 'id')].lstrip('/')
      sheet_file = target if target.startswith('xl/') else 'xl/' + target
      break
  if sheet_file is None:
    raise KeyError(f"worksheet '{sheet_name}' not found")

  try:
    shared = ET.fromstring(archive.read('xl/sharedStrings.xml'))
    strings = [''.join(t.text or '' for t in si.iter(_XLSX_NS + 't')) for si in shared]
  except KeyError:
    strings = []

  rows = []
  for row in ET.fromstring(archive.read(sheet_file)).iter(_XLSX_NS + 'row'):
    cells = {}
    for cell in row.iter(_XLSX_NS + 'c'):
      column = re.match(r'[A-Z]+', cell.get('r')).group()
      kind = cell.get('t')
      if kind == 'inlineStr':
        value = ''.join(t.text or '' for t in cell.iter(_XLSX_NS + 't'))
      else:
        v = cell.find(_XLSX_NS + 'v')
        value = v.text or '' if v is not None else ''
        if kind == 's':
          value = strings[int(value)]
      cells[column] = value
    rows.append(cells)

  header = rows[0] if rows else {}
  return header, rows[1:]


class DeckValidator:
  """Cross-validates a nanDECK script and its linked spreadsheet."""

  def __init__(self, script_path):
    self.script_path = script_path
    self.base_dir = os.path.dirname(os.path.abspath(script_path)) or '.'
    self.findings = []

  def error(self, line, message, file=None):
    self.findings.append(Finding('error', file or os.path.basename(self.script_path), line, message))

  def warning(self, line, message, file=None):
    self.findings.append(Finding('warning', file or os.path.basename(self.script_path), line, message))

  def run(self):
    try:
      script = parse_script(self.script_path)
    except OSError as ex:
      self.error(0, f"cannot read script: {ex}")
      return self.findings

    self._check_directives_known(script)
    self._check_duplex_cards_conflict(script)
    self._check_visual_blocks(script)
    self._check_expressions(script)
    self._check_colors(script)
    self._check_file_references(script)
    icon_codes = self._check_icon_definitions(script)

    columns, rows, data_file = self._load_linked_data(script)
    self._check_label_references(script, columns)
    if rows is not None:
      self._check_link_multi(script, columns)
      self._check_data_rows(script, columns, rows, data_file, icon_codes)
      self._check_card_count(script, columns, rows)

    return self.findings

  # -- script checks ---------------------------------------------------------

  def _check_directives_known(self, script):
    for directive in script.directives:
      if directive.name not in KNOWN_DIRECTIVES:
        self.warning(directive.line, f"unknown directive '{directive.name}'")

  def _check_duplex_cards_conflict(self, script):
    duplex = script.first('DUPLEX')
    cards = script.first('CARDS')
    if duplex and cards:
      self.error(cards.line, "CARDS must not be used together with DUPLEX (nanDECK needs to add cards to the deck)")

  def _check_visual_blocks(self, script):
    depth = 0
    for directive in script.directives:
      if directive.name == 'VISUAL':
        depth += 1
      elif directive.name == 'ENDVISUAL':
        depth -= 1
        if depth < 0:
          self.error(directive.line, "ENDVISUAL without matching VISUAL")
          depth = 0
    if depth > 0:
      self.error(0, "VISUAL block is never closed (missing ENDVISUAL)")

  def _check_expressions(self, script):
    for directive in script.directives:
      text = directive.value
      if text.count('{') != text.count('}'):
        self.error(directive.line, "unbalanced braces in expression")
        continue
      for expression in re.findall(r'\{([^{}]*)\}', text):
        if not re.fullmatch(r'[0-9+\-*/(). ]+', expression):
          continue  # references like {(ID)} are resolved by nanDECK at runtime
        try:
          eval(compile(expression, '<expr>', 'eval'), {'__builtins__': {}}, {})
        except ZeroDivisionError:
          self.error(directive.line, f"division by zero in expression {{{expression}}}")
        except SyntaxError:
          self.error(directive.line, f"malformed expression {{{expression}}}")

  def _check_colors(self, script):
    for directive in script.directives:
      for color in re.findall(r'#[0-9A-Fa-f]+\b', directive.value):
        if len(color) - 1 not in (6, 8):  # #RRGGBB or #RRGGBBAA
          self.error(directive.line, f"malformed color literal '{color}' (expected #RRGGBB)")

  def _check_file_references(self, script):
    for directive in script.directives:
      for quoted in re.findall(r'"([^"]+)"', directive.value):
        if not quoted.lower().endswith(IMAGE_EXTENSIONS):
          continue
        self._check_referenced_file(directive.line, quoted)

  def _check_referenced_file(self, line, reference):
    if is_absolute_reference(reference):
      self.error(line, f"absolute path '{reference}' breaks portable builds; use a repository-relative path")
    elif not exists_with_exact_case(self.base_dir, reference):
      self.error(line, f"referenced file '{reference}' not found (paths are case-sensitive)")

  def _check_icon_definitions(self, script):
    codes = {}
    for directive in script.all('ICON'):
      fields = split_fields(directive.value)
      if len(fields) < 3:
        self.error(directive.line, "ICON needs <range>,<code>,<image>")
        continue
      code = unquote(fields[1])
      if len(code) != 1:
        self.error(directive.line, f"icon code '{code}' must be a single character")
        continue
      if code in codes:
        self.error(directive.line, f"icon code '{code}' already defined on line {codes[code]}")
      codes[code] = directive.line
    return set(codes)

  # -- linked data checks ----------------------------------------------------

  def _load_linked_data(self, script):
    link = script.first('LINK')
    if link is None:
      return set(), None, None
    reference = unquote(split_fields(link.value)[0])
    file_part, _, sheet_part = reference.partition('!')
    if is_absolute_reference(file_part):
      self.error(link.line, f"absolute LINK path '{file_part}' breaks portable builds; use a repository-relative path")
      return set(), None, None
    if not exists_with_exact_case(self.base_dir, file_part):
      self.error(link.line, f"linked data file '{file_part}' not found (paths are case-sensitive)")
      return set(), None, None
    try:
      header, rows = load_xlsx(os.path.join(self.base_dir, file_part), sheet_part or None)
    except (KeyError, zipfile.BadZipFile, ET.ParseError) as ex:
      self.error(link.line, f"cannot read linked data file '{file_part}': {ex}")
      return set(), None, None
    columns = {value.strip().lower(): letter for letter, value in header.items() if value.strip()}
    return columns, rows, os.path.basename(file_part)

  def _check_label_references(self, script, columns):
    sources = [(d.line, d.value) for d in script.directives]
    sources += [(line, value) for line, value in script.labels.values()]
    for line, value in sources:
      for label in re.findall(r'\[([A-Za-z][A-Za-z0-9_]*)\]', value):
        if label.lower() not in script.labels and label.lower() not in columns:
          self.error(line, f"label or column '[{label}]' is neither defined in the script nor a spreadsheet column")

  def _check_link_multi(self, script, columns):
    directive = script.first('LINKMULTI')
    if directive and directive.value.strip().lower() not in columns:
      self.error(directive.line, f"LINKMULTI column '{directive.value.strip()}' not found in linked data")

  def _check_data_rows(self, script, columns, rows, data_file, icon_codes):
    multi = script.first('LINKMULTI')
    count_column = columns.get(multi.value.strip().lower()) if multi else None
    icon_columns = self._icon_text_columns(script, columns)

    for index, row in enumerate(rows, start=2):  # 1-based plus header row
      if not any(value.strip() for value in row.values()):
        continue  # structurally empty rows are skipped by nanDECK

      if count_column:
        count = row.get(count_column, '').strip()
        if count and (not count.lstrip('-').isdigit() or int(count) < 0):
          self.error(index, f"count '{count}' must be a non-negative integer", file=data_file)

      for letter, value in row.items():
        value = value.strip()
        if not value:
          continue
        if re.fullmatch(r'#[0-9A-Fa-f]*', value) and len(value) - 1 not in (6, 8):
          self.error(index, f"malformed color literal '{value}' (expected #RRGGBB)", file=data_file)
        elif value.lower().endswith(IMAGE_EXTENSIONS):
          if is_absolute_reference(value):
            self.error(index, f"absolute path '{value}' breaks portable builds", file=data_file)
          elif not exists_with_exact_case(self.base_dir, value):
            self.error(index, f"referenced file '{value}' not found (paths are case-sensitive)", file=data_file)
        if letter in icon_columns:
          for char in value:
            if char not in icon_codes and char not in '<>':
              self.error(index, f"icon flag '{char}' has no ICON definition in the script", file=data_file)

  def _icon_text_columns(self, script, columns):
    """Column letters whose values are rendered through ICONS directives."""
    letters = set()
    for directive in script.all('ICONS'):
      fields = split_fields(directive.value)
      if len(fields) < 2:
        continue
      match = re.fullmatch(r'\[([A-Za-z][A-Za-z0-9_]*)\]', fields[1])
      if match and match.group(1).lower() in columns:
        letters.add(columns[match.group(1).lower()])
    return letters

  def _check_card_count(self, script, columns, rows):
    directive = script.first('CARDS')
    multi = script.first('LINKMULTI')
    if directive is None or multi is None:
      return
    count_column = columns.get(multi.value.strip().lower())
    if count_column is None:
      return
    generated = sum(
        int(row.get(count_column, '').strip() or 0)
        for row in rows
        if any(value.strip() for value in row.values()) and row.get(count_column, '').strip().isdigit()
    )
    declared = directive.value.strip()
    if declared.isdigit() and int(declared) != generated:
      self.warning(
          directive.line,
          f"CARDS={declared} overrides the {generated} cards generated from the linked data; the rendered deck will be truncated or padded"
      )


def main(argv):
  script_path = argv[1] if len(argv) > 1 else 'Game.nde'
  if not os.path.isfile(script_path):
    print(f"ERROR: script '{script_path}' not found", file=sys.stderr)
    return 1

  findings = DeckValidator(script_path).run()
  in_ci = os.environ.get('GITHUB_ACTIONS') == 'true'
  for finding in findings:
    print(finding.as_annotation() if in_ci else str(finding))

  errors = sum(1 for finding in findings if finding.level == 'error')
  warnings = len(findings) - errors
  print(f"{os.path.basename(script_path)}: {errors} error(s), {warnings} warning(s)")
  return 1 if errors else 0


if __name__ == '__main__':
  sys.exit(main(sys.argv))
