# -*- coding: utf-8 -*-
"""Tests for Scripts/validate_deck.py (pytest).

Each test follows given-when-then; fixtures build minimal deck projects in
tmp_path so script and data checks are exercised in isolation.
"""
import os
import sys
import zipfile
from xml.sax.saxutils import escape

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Scripts'))
from validate_deck import DeckValidator, load_xlsx, parse_script  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
       b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
       b'\x00\x00\x05\x00\x01\r\n\x2d\xb4\x00\x00\x00\x00IEND\xaeB`\x82')


def column_letter(index):
  letters = ''
  while index >= 0:
    letters = chr(ord('A') + index % 26) + letters
    index = index // 26 - 1
  return letters


def make_xlsx(path, rows, sheet_name='Cards'):
  """Writes a minimal xlsx (inline strings only) readable by load_xlsx."""
  sheet_rows = []
  for row_number, row in enumerate(rows, start=1):
    cells = ''.join(
        f'<c r="{column_letter(i)}{row_number}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
        for i, value in enumerate(row)
    )
    sheet_rows.append(f'<row r="{row_number}">{cells}</row>')
  sheet_xml = (
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
      f'<sheetData>{"".join(sheet_rows)}</sheetData></worksheet>'
  )
  with zipfile.ZipFile(path, 'w') as archive:
    archive.writestr('[Content_Types].xml',
                     '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                     '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
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
                     f'<sheets><sheet name="{sheet_name}" sheetId="1" r:id="rId1"/></sheets></workbook>')
    archive.writestr('xl/_rels/workbook.xml.rels',
                     '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                     '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                     '</Relationships>')
    archive.writestr('xl/worksheets/sheet1.xml', sheet_xml)


@pytest.fixture
def project(tmp_path):
  """A minimal valid deck project: script, data, icon and face artwork."""
  (tmp_path / 'Icons').mkdir()
  (tmp_path / 'Icons' / 'Fire.png').write_bytes(PNG)
  (tmp_path / 'Face.png').write_bytes(PNG)
  make_xlsx(tmp_path / 'Cards.xlsx', [
      ['Count', 'Name', 'HtmlColor', 'FaceImage', 'CardIcons'],
      ['1', 'Alpha', '#FF0000', 'Face.png', 'F'],
      ['2', 'Beta', '#00FF00', 'Face.png', ''],
  ])

  def write(script_text):
    script = tmp_path / 'Game.nde'
    script.write_text(script_text, encoding='cp1252')
    return str(script)

  def validate(script_text):
    return DeckValidator(write(script_text)).run()

  def errors(script_text):
    return [f for f in validate(script_text) if f.level == 'error']

  validate.write = write
  validate.errors = errors
  validate.path = tmp_path
  return validate


VALID_SCRIPT = '''\
UNIT=MM
PAGE=210,297,PORTRAIT,HV
CARDSIZE=56,87
LINKMULTI=Count
LINK=Cards.xlsx
[all]=1-{(Name)}
ICON=,F,"Icons\\Fire.png"
VISUAL=HVG,10,10
IMAGE=[all],"Face.png",0%,0%,100%,100%,0,NA
RECTANGLE=[all],0%,0%,100%,5%,[HTMLCOLOR]
ICONS=[all],[CARDICONS],0%,0%,10%,10%,10%,10%,0,NPA,CENTER,CENTER
TEXT=[all],[NAME],{10863/322}%,10%,50%,10%,CENTER,CENTER
ENDVISUAL
'''


class TestHappyPath:

  def test_given_valid_project_when_validating_then_no_findings(self, project):
    assert project(VALID_SCRIPT) == []

  def test_given_comments_and_blank_lines_when_parsing_then_ignored(self, project):
    assert project.errors(';just a comment\n\n' + VALID_SCRIPT) == []


class TestDirectives:

  def test_given_unknown_directive_when_validating_then_warning_not_error(self, project):
    findings = project(VALID_SCRIPT + 'FLUXCAPACITOR=88\n')
    assert [f.level for f in findings] == ['warning']
    assert "FLUXCAPACITOR" in findings[0].message

  def test_given_missing_endvisual_when_validating_then_error(self, project):
    findings = project.errors(VALID_SCRIPT.replace('ENDVISUAL\n', ''))
    assert any('never closed' in f.message for f in findings)

  def test_given_endvisual_without_visual_when_validating_then_error(self, project):
    findings = project.errors('ENDVISUAL\n' + VALID_SCRIPT)
    assert any('without matching VISUAL' in f.message for f in findings)


class TestExpressions:

  def test_given_unbalanced_braces_when_validating_then_error(self, project):
    findings = project.errors(VALID_SCRIPT + 'CIRCLE=[all],{755/161%,1%,1%,1%,#FFFFFF\n')
    assert any('unbalanced braces' in f.message for f in findings)

  def test_given_division_by_zero_when_validating_then_error(self, project):
    findings = project.errors(VALID_SCRIPT + 'CIRCLE=[all],{755/0}%,1%,1%,1%,#FFFFFF\n')
    assert any('division by zero' in f.message for f in findings)

  def test_given_runtime_reference_in_braces_when_validating_then_not_evaluated(self, project):
    assert project.errors(VALID_SCRIPT + 'CARDS={(Name)}\n') == []


class TestColors:

  @pytest.mark.parametrize('color', ['#FFFFFF', '#000000', '#FF0000AA'])
  def test_given_valid_color_when_validating_then_no_error(self, project, color):
    assert project.errors(VALID_SCRIPT + f'RECTANGLE=[all],0%,0%,1%,1%,{color}\n') == []

  @pytest.mark.parametrize('color', ['#FFFFF', '#FFFFFFF', '#AB'])
  def test_given_color_with_wrong_digit_count_when_validating_then_error(self, project, color):
    findings = project.errors(VALID_SCRIPT + f'RECTANGLE=[all],0%,0%,1%,1%,{color}\n')
    assert any('malformed color' in f.message for f in findings)


class TestFileReferences:

  def test_given_missing_image_when_validating_then_error(self, project):
    findings = project.errors(VALID_SCRIPT + 'IMAGE=[all],"Ghost.png",0%,0%,100%,100%,0,NA\n')
    assert any("'Ghost.png' not found" in f.message for f in findings)

  def test_given_wrong_case_image_when_validating_then_error(self, project):
    findings = project.errors(VALID_SCRIPT.replace('"Face.png"', '"face.png"'))
    assert any('case-sensitive' in f.message for f in findings)

  def test_given_absolute_image_path_when_validating_then_error(self, project):
    findings = project.errors(VALID_SCRIPT + 'IMAGE=[all],"X:\\Somewhere\\Face.png",0%,0%,100%,100%,0,NA\n')
    assert any('absolute path' in f.message for f in findings)


class TestLink:

  def test_given_absolute_link_path_when_validating_then_error(self, project):
    findings = project.errors(VALID_SCRIPT.replace('LINK=Cards.xlsx', 'LINK=X:\\Users\\Nobody\\Cards.xlsx'))
    assert any('absolute LINK path' in f.message for f in findings)

  def test_given_missing_link_file_when_validating_then_error(self, project):
    findings = project.errors(VALID_SCRIPT.replace('LINK=Cards.xlsx', 'LINK=Ghost.xlsx'))
    assert any("'Ghost.xlsx' not found" in f.message for f in findings)

  def test_given_linkmulti_without_matching_column_when_validating_then_error(self, project):
    findings = project.errors(VALID_SCRIPT.replace('LINKMULTI=Count', 'LINKMULTI=Amount'))
    assert any("LINKMULTI column 'Amount'" in f.message for f in findings)


class TestLabels:

  def test_given_unresolved_label_when_validating_then_error(self, project):
    findings = project.errors(VALID_SCRIPT + 'TEXT=[all],[GHOSTCOLUMN],0%,0%,10%,10%\n')
    assert any("'[GHOSTCOLUMN]'" in f.message for f in findings)

  def test_given_label_defined_in_script_when_used_then_resolved_case_insensitively(self, project):
    assert project.errors(VALID_SCRIPT + '[MyVar]="static"\nTEXT=[all],[MYVAR],0%,0%,10%,10%\n') == []


class TestIconDefinitions:

  def test_given_two_character_icon_code_when_validating_then_error(self, project):
    findings = project.errors(VALID_SCRIPT + 'ICON=,XY,"Icons\\Fire.png"\n')
    assert any("must be a single character" in f.message for f in findings)

  def test_given_duplicate_icon_code_when_validating_then_error(self, project):
    findings = project.errors(VALID_SCRIPT + 'ICON=,F,"Icons\\Fire.png"\n')
    assert any("already defined" in f.message for f in findings)


class TestDataRows:

  @pytest.mark.parametrize('count', ['abc', '-1', '1.5'])
  def test_given_non_numeric_or_negative_count_when_validating_then_error(self, project, count):
    make_xlsx(project.path / 'Cards.xlsx', [
        ['Count', 'Name', 'HtmlColor', 'FaceImage', 'CardIcons'],
        [count, 'Alpha', '#FF0000', 'Face.png', ''],
    ])
    findings = project.errors(VALID_SCRIPT)
    assert any('non-negative integer' in f.message for f in findings)

  @pytest.mark.parametrize('count', ['0', '1', '99', ''])
  def test_given_boundary_count_values_when_validating_then_accepted(self, project, count):
    make_xlsx(project.path / 'Cards.xlsx', [
        ['Count', 'Name', 'HtmlColor', 'FaceImage', 'CardIcons'],
        [count, 'Alpha', '#FF0000', 'Face.png', ''],
    ])
    assert project.errors(VALID_SCRIPT) == []

  def test_given_malformed_color_in_data_when_validating_then_error_names_data_file(self, project):
    make_xlsx(project.path / 'Cards.xlsx', [
        ['Count', 'Name', 'HtmlColor', 'FaceImage', 'CardIcons'],
        ['1', 'Alpha', '#FF00', 'Face.png', ''],
    ])
    findings = project.errors(VALID_SCRIPT)
    assert any('malformed color' in f.message and f.file == 'Cards.xlsx' for f in findings)

  def test_given_missing_face_image_in_data_when_validating_then_error(self, project):
    make_xlsx(project.path / 'Cards.xlsx', [
        ['Count', 'Name', 'HtmlColor', 'FaceImage', 'CardIcons'],
        ['1', 'Alpha', '#FF0000', 'Ghost.png', ''],
    ])
    findings = project.errors(VALID_SCRIPT)
    assert any("'Ghost.png' not found" in f.message for f in findings)

  def test_given_undefined_icon_flag_when_validating_then_error(self, project):
    make_xlsx(project.path / 'Cards.xlsx', [
        ['Count', 'Name', 'HtmlColor', 'FaceImage', 'CardIcons'],
        ['1', 'Alpha', '#FF0000', 'Face.png', 'Z'],
    ])
    findings = project.errors(VALID_SCRIPT)
    assert any("icon flag 'Z'" in f.message for f in findings)

  def test_given_icon_flags_with_size_separators_when_validating_then_accepted(self, project):
    make_xlsx(project.path / 'Cards.xlsx', [
        ['Count', 'Name', 'HtmlColor', 'FaceImage', 'CardIcons'],
        ['1', 'Alpha', '#FF0000', 'Face.png', 'F<F'],
    ])
    assert project.errors(VALID_SCRIPT) == []

  def test_given_fully_empty_row_when_validating_then_skipped(self, project):
    make_xlsx(project.path / 'Cards.xlsx', [
        ['Count', 'Name', 'HtmlColor', 'FaceImage', 'CardIcons'],
        ['', '', '', '', ''],
        ['1', 'Alpha', '#FF0000', 'Face.png', ''],
    ])
    assert project.errors(VALID_SCRIPT) == []


class TestDuplex:

  def test_given_duplex_and_cards_together_when_validating_then_error(self, project):
    findings = project.errors(VALID_SCRIPT + 'DUPLEX=[all],1\nCARDS=3\n')
    assert any('must not be used together with DUPLEX' in f.message for f in findings)

  def test_given_duplex_without_cards_when_validating_then_no_error(self, project):
    assert project.errors(VALID_SCRIPT + 'DUPLEX=[all],1\nPRINT=DUPLEX\n') == []


class TestCardCount:

  def test_given_cards_directive_mismatching_generated_count_when_validating_then_warning(self, project):
    findings = project(VALID_SCRIPT + 'CARDS=25\n')
    assert any(f.level == 'warning' and 'CARDS=25' in f.message and '3 cards' in f.message for f in findings)

  def test_given_cards_directive_matching_generated_count_when_validating_then_no_warning(self, project):
    assert project(VALID_SCRIPT + 'CARDS=3\n') == []


class TestRealDeck:
  """Integration: the repository's actual deck must validate cleanly."""

  def test_given_repository_deck_when_validating_then_no_errors(self):
    findings = DeckValidator(os.path.join(REPO_ROOT, 'Game.nde')).run()
    assert [f for f in findings if f.level == 'error'] == []

  def test_given_repository_data_when_loading_then_expected_columns_and_266_cards(self):
    header, rows = load_xlsx(os.path.join(REPO_ROOT, 'Cards.xlsx'), 'Cards')
    names = {value.strip().lower() for value in header.values()}
    assert {'count', 'name', 'htmlcolor', 'faceimage', 'cardicons'} <= names
    count_column = next(letter for letter, value in header.items() if value.strip().lower() == 'count')
    total = sum(int(row[count_column]) for row in rows if row.get(count_column, '').strip().isdigit())
    assert total == 266

  def test_given_repository_script_when_parsing_then_link_is_relative(self):
    script = parse_script(os.path.join(REPO_ROOT, 'Game.nde'))
    link = script.first('LINK')
    assert link is not None
    assert ':' not in link.value
