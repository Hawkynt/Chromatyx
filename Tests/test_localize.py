# -*- coding: utf-8 -*-
"""Tests for Scripts/localize.py (pytest)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Scripts'))
from localize import (load_translations, localize_rows, localize_workbook,  # noqa: E402
                      translate, write_xlsx)
from validate_deck import load_xlsx  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
WORKBOOK = os.path.join(REPO_ROOT, 'Cards.xlsx')

MAPPING = {
    'Erde': 'Earth',
    'Blockade': 'Block',
    'Prisma': 'Rainbow',
    'Fokus': 'Focus',
    'Neptun': 'Neptune',
    'Falle': 'Trap',
    'Nächster Spieler muss aussetzen': 'Next player sits out',
}


class TestTranslate:

  def test_given_exact_phrase_when_translating_then_full_match_wins(self):
    assert translate('Nächster Spieler muss aussetzen', MAPPING) == 'Next player sits out'

  def test_given_composite_value_when_translating_then_tokens_replaced(self):
    assert translate('Prisma Fokus +2', MAPPING) == 'Rainbow Focus +2'
    assert translate('Erde Blockade', MAPPING) == 'Earth Block'

  def test_given_substring_of_longer_word_when_translating_then_untouched(self):
    # 'Neptun' must not fire inside 'Neptune' (word boundary)
    assert translate(r'Planets\Neptune.png', MAPPING) == r'Planets\Neptune.png'

  @pytest.mark.parametrize('value', ['', '#FF0000', '+2', '☉0', 'R<X<D'])
  def test_given_untranslatable_values_when_translating_then_identity(self, value):
    assert translate(value, MAPPING) == value

  def test_given_empty_mapping_when_translating_then_identity(self):
    assert translate('Erde Blockade', {}) == 'Erde Blockade'


class TestLocalizeRows:

  def test_given_rows_when_localizing_then_header_untouched_and_cells_translated(self):
    header = {'A': 'Type', 'B': 'Name'}
    rows = [{'A': 'Falle', 'B': 'Erde Blockade'}, {}]
    out_header, out_rows = localize_rows(header, rows, MAPPING)
    assert out_header == header
    assert out_rows == [{'A': 'Trap', 'B': 'Earth Block'}, {}]


class TestWriteXlsx:

  def test_given_written_workbook_when_reading_back_then_values_round_trip(self, tmp_path):
    path = str(tmp_path / 'out.xlsx')
    header = {'A': 'Count', 'B': 'Name'}
    rows = [{'A': '1', 'B': 'Sun 0'}, {}, {'A': '2', 'B': 'Träger & <Sohn>'}]
    write_xlsx(path, 'Cards', header, rows)
    read_header, read_rows = load_xlsx(path, 'Cards')
    assert read_header == header
    assert read_rows == [{'A': '1', 'B': 'Sun 0'}, {}, {'A': '2', 'B': 'Träger & <Sohn>'}]

  def test_given_written_workbook_when_inspecting_then_uses_shared_strings(self, tmp_path):
    # nanDECK's reader fails on inline strings; the conventional layout is required.
    import zipfile
    path = str(tmp_path / 'out.xlsx')
    write_xlsx(path, 'Cards', {'A': 'Name'}, [{'A': 'Sun'}])
    names = zipfile.ZipFile(path).namelist()
    assert 'xl/sharedStrings.xml' in names
    assert 'xl/styles.xml' in names
    assert b'inlineStr' not in zipfile.ZipFile(path).read('xl/worksheets/sheet1.xml')


class TestRealWorkbook:
  """Integration against the repository's Cards.xlsx."""

  def test_given_unknown_culture_when_loading_then_helpful_error(self):
    with pytest.raises(KeyError, match='fr-FR'):
      load_translations(WORKBOOK, 'fr-FR')

  def test_given_source_culture_when_loading_then_identity_mapping(self):
    assert load_translations(WORKBOOK, 'de-DE') == {}

  def test_given_en_us_when_localizing_then_types_and_names_fully_english(self, tmp_path):
    output = str(tmp_path / 'Cards.en-US.xlsx')
    localize_workbook(WORKBOOK, 'en-US', output)
    header, rows = load_xlsx(output, 'Cards')
    columns = {value.strip().lower(): letter for letter, value in header.items()}
    types = {row[columns['type']] for row in rows if row.get(columns['type'], '').strip()}
    assert types == {'Normal', 'Action', 'Trap', 'Guard', 'Backface'}
    names = {row.get(columns['name'], '') for row in rows}
    assert 'Sun 0' in names and 'Earth Block' in names

  def test_given_en_us_when_localizing_then_paths_icons_and_counts_unchanged(self, tmp_path):
    output = str(tmp_path / 'Cards.en-US.xlsx')
    localize_workbook(WORKBOOK, 'en-US', output)
    de_header, de_rows = load_xlsx(WORKBOOK, 'Cards')
    en_header, en_rows = load_xlsx(output, 'Cards')
    columns = {value.strip().lower(): letter for letter, value in de_header.items()}
    for stable in ('count', 'htmlcolor', 'faceimage', 'cardicons', 'symbol'):
      letter = columns[stable]
      assert [r.get(letter, '') for r in de_rows] == [r.get(letter, '') for r in en_rows], stable

  def test_given_en_us_when_localizing_then_no_german_phrases_survive(self, tmp_path):
    import re
    output = str(tmp_path / 'Cards.en-US.xlsx')
    localize_workbook(WORKBOOK, 'en-US', output)
    _, rows = load_xlsx(output, 'Cards')
    pattern = re.compile(r'(?<!\w)(Spieler|Karten|Farbe|Wähle|muss|Runde|Zug|Effekte)(?!\w)')
    leftovers = [value for row in rows for value in row.values() if pattern.search(value)]
    assert leftovers == []
