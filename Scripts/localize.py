#!/usr/bin/env python3
"""Generates localized card data for the Chromatyx deck.

The workbook localizes itself through Excel formulas (the Localization sheet
plus the CURRENT_CULTURE_INDEX named range), but nanDECK reads cached cell
values and never recalculates formulas - so simply switching the language in
the Config sheet does nothing for a headless render. This script applies the
Localization mapping to the cached Cards values directly and writes a
standalone per-culture workbook that nanDECK can link.

Usage: localize.py <culture> [--workbook Cards.xlsx] [--output <file>]

Example: localize.py en-US            -> writes Cards.en-US.xlsx

Only the Python standard library is used.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import zipfile
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_deck import load_xlsx  # noqa: E402

SOURCE_CULTURE = 'de-DE'  # the culture the cached Cards values are in
CARDS_SHEET = 'Cards'
LOCALIZATION_SHEET = 'Localization'


def load_translations(workbook_path, culture):
  """Returns the {source phrase: translated phrase} mapping for a culture.

  The Localization sheet holds one column per culture ('Current' is the
  formula-driven column and is ignored). Asking for the source culture yields
  an empty mapping (identity).
  """
  header, rows = load_xlsx(workbook_path, LOCALIZATION_SHEET)
  columns = {value.strip(): letter for letter, value in header.items() if value.strip()}
  if culture not in columns:
    known = ', '.join(sorted(c for c in columns if c != 'Current'))
    raise KeyError(f"culture '{culture}' not found in {LOCALIZATION_SHEET} sheet (available: {known})")
  if culture == SOURCE_CULTURE:
    return {}

  source_column, target_column = columns[SOURCE_CULTURE], columns[culture]
  translations = {}
  for row in rows:
    source = row.get(source_column, '').strip()
    target = row.get(target_column, '').strip()
    if source and target:
      translations[source] = target
  return translations


def translate(value, translations):
  """Translates one cell value.

  Exact phrases win (effect sentences are stored verbatim in the mapping);
  otherwise known phrases are replaced longest-first with word boundaries, so
  composites like 'Prisma Fokus +2' become 'Rainbow Focus +2' while
  'Planets\\Neptune.png' is never mangled by the key 'Neptun'.
  """
  if not value or not translations:
    return value
  exact = translations.get(value.strip())
  if exact is not None:
    return exact
  result = value
  for source in sorted(translations, key=len, reverse=True):
    result = re.sub(rf'(?<!\w){re.escape(source)}(?!\w)', translations[source].replace('\\', '\\\\'), result)
  return result


def localize_rows(header, rows, translations):
  """Returns (header, rows) with every data cell translated; the header row
  holds column identifiers referenced by the deck script and stays as-is."""
  return header, [
      {letter: translate(value, translations) for letter, value in row.items()}
      for row in rows
  ]


def write_xlsx(path, sheet_name, header, rows):
  """Writes a minimal single-sheet workbook.

  Strings go through xl/sharedStrings.xml (cells with t="s") and the sheet
  carries a dimension element - the conventional layout Excel itself produces.
  nanDECK's reader requires this shape; it fails on inline strings with a
  'List index out of bounds' error.
  """
  strings, string_ids = [], {}

  def string_id(value):
    if value not in string_ids:
      string_ids[value] = len(strings)
      strings.append(value)
    return string_ids[value]

  def row_xml(row_number, cells):
    parts = ''.join(
        f'<c r="{letter}{row_number}" t="s"><v>{string_id(value)}</v></c>'
        for letter, value in sorted(cells.items(), key=lambda kv: (len(kv[0]), kv[0]))
        if value != ''
    )
    return f'<row r="{row_number}">{parts}</row>'

  all_rows = [header] + list(rows)
  sheet_rows = [row_xml(number, cells) for number, cells in enumerate(all_rows, start=1)]
  last_column = max((letter for cells in all_rows for letter in cells), key=lambda c: (len(c), c), default='A')
  sheet_xml = (
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
      f'<dimension ref="A1:{last_column}{len(all_rows)}"/>'
      f'<sheetData>{"".join(sheet_rows)}</sheetData></worksheet>'
  )
  shared_xml = (
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(strings)}" uniqueCount="{len(strings)}">'
      + ''.join(f'<si><t xml:space="preserve">{escape(value)}</t></si>' for value in strings)
      + '</sst>'
  )
  styles_xml = (
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
      '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
      '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
      '<borders count="1"><border/></borders>'
      '<cellStyleXfs count="1"><xf/></cellStyleXfs>'
      '<cellXfs count="1"><xf xfId="0"/></cellXfs>'
      '</styleSheet>'
  )
  with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
    archive.writestr('[Content_Types].xml',
                     '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                     '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                     '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
                     '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                     '</Types>')
    archive.writestr('_rels/.rels',
                     '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                     '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                     '</Relationships>')
    archive.writestr('xl/workbook.xml',
                     '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                     'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                     f'<sheets><sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets></workbook>')
    archive.writestr('xl/_rels/workbook.xml.rels',
                     '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                     '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                     '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
                     '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                     '</Relationships>')
    archive.writestr('xl/worksheets/sheet1.xml', sheet_xml)
    archive.writestr('xl/sharedStrings.xml', shared_xml)
    archive.writestr('xl/styles.xml', styles_xml)


def localize_workbook(workbook_path, culture, output_path):
  translations = load_translations(workbook_path, culture)
  header, rows = load_xlsx(workbook_path, CARDS_SHEET)
  header, rows = localize_rows(header, rows, translations)
  write_xlsx(output_path, CARDS_SHEET, header, rows)
  return len(translations)


def main(argv):
  parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  parser.add_argument('culture', help="target culture, e.g. en-US")
  parser.add_argument('--workbook', default='Cards.xlsx')
  parser.add_argument('--output', default=None, help="defaults to Cards.<culture>.xlsx next to the workbook")
  args = parser.parse_args(argv)

  output = args.output
  if output is None:
    base, extension = os.path.splitext(args.workbook)
    output = f'{base}.{args.culture}{extension}'

  phrases = localize_workbook(args.workbook, args.culture, output)
  print(f"{output}: localized to {args.culture} using {phrases} phrase(s)")
  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
