# -*- coding: utf-8 -*-
"""Tests keeping the two rulebook translations and the deck data in sync."""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Scripts'))
from validate_deck import load_xlsx  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RULEBOOKS = {
    'de-DE': os.path.join(REPO_ROOT, 'Rulebook.de-DE.md'),
    'en-US': os.path.join(REPO_ROOT, 'Rulebook.en-US.md'),
}


def read(culture):
  with open(RULEBOOKS[culture], 'r', encoding='utf-8') as f:
    return f.read()


def structure(text):
  """(heading counts per level, table row counts per table) - the
  language-independent skeleton both translations must share."""
  headings = [len(m) for m in re.findall(r'^(#+) ', text, re.M)]
  tables, current = [], 0
  for line in text.splitlines() + ['']:
    if line.startswith('|') and not re.match(r'^\|[\s:|-]+\|$', line):
      current += 1
    elif current:
      tables.append(current)
      current = 0
  return headings, tables


class TestTranslationParity:

  def test_given_both_rulebooks_when_comparing_then_same_heading_structure(self):
    de, en = structure(read('de-DE')), structure(read('en-US'))
    assert de[0] == en[0], 'heading levels/order must match between translations'

  def test_given_both_rulebooks_when_comparing_then_same_table_shapes(self):
    de, en = structure(read('de-DE')), structure(read('en-US'))
    assert de[1] == en[1], 'tables and their row counts must match between translations'


class TestDeckConsistency:
  """The numbers and names in the rulebooks must match Cards.xlsx."""

  @pytest.fixture(scope='class')
  def deck(self):
    header, rows = load_xlsx(os.path.join(REPO_ROOT, 'Cards.xlsx'), 'Cards')
    columns = {value.strip().lower(): letter for letter, value in header.items()}
    return columns, rows

  def total(self, deck, predicate=lambda row: True):
    columns, rows = deck
    return sum(int(row[columns['count']])
               for row in rows
               if row.get(columns['count'], '').strip().isdigit()
               and row.get(columns['type'], '') != 'Backface' and predicate(row))

  @pytest.mark.parametrize('culture', ['de-DE', 'en-US'])
  def test_given_rulebook_when_checking_total_then_265_playing_cards(self, deck, culture):
    assert self.total(deck) == 265
    assert '265' in read(culture)

  @pytest.mark.parametrize('culture', ['de-DE', 'en-US'])
  def test_given_rulebook_when_checking_groups_then_counts_match_deck(self, deck, culture):
    columns, _ = deck
    black = self.total(deck, lambda r: r.get(columns['color']) == 'Black')
    white = self.total(deck, lambda r: r.get(columns['color']) == 'White')
    planets = self.total(deck) - black - white
    text = read(culture)
    for count in (planets, black, white):
      assert str(count) in text, f'count {count} missing in {culture} rulebook'

  def test_given_de_rulebook_when_checking_names_then_card_names_from_deck_present(self):
    text = read('de-DE')
    for name in ('Umkehrung', 'Blockade', 'Wiederholung', 'Eis', 'Feuer', 'Fokus',
                 'Prisma', 'Schild', 'Spiegel'):
      assert name in text, f'{name} missing in German rulebook'

  def test_given_en_rulebook_when_checking_names_then_localized_names_present(self):
    header, rows = load_xlsx(os.path.join(REPO_ROOT, 'Cards.xlsx'), 'Localization')
    columns = {value.strip(): letter for letter, value in header.items()}
    mapping = {row.get(columns['de-DE'], ''): row.get(columns['en-US'], '') for row in rows}
    text = read('en-US')
    for de_name in ('Umkehrung', 'Blockade', 'Wiederholung', 'Eis', 'Feuer', 'Fokus',
                    'Prisma', 'Schild', 'Spiegel'):
      en_name = mapping[de_name]
      assert en_name in text, f'{en_name} (for {de_name}) missing in English rulebook'
      assert de_name not in text, f'untranslated {de_name} found in English rulebook'
