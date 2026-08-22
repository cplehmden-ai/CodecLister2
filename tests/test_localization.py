"""Tests fuer eingebaute und benutzerdefinierte PO-Uebersetzungen."""

from codeclister.localization import Translation, available_translations


def test_builtin_translations_are_available():
    translations = {item.language: item for item in available_translations()}
    assert translations["de"].gettext("Choose folder...") == "Ordner waehlen..."
    assert translations["en"].gettext("Choose folder...") == "Choose folder..."
    assert translations["de"].display_name == "Deutsch"


def test_custom_po_translation(tmp_path):
    (tmp_path / "fr.po").write_text(
        'msgid ""\n'
        'msgstr ""\n'
        '"Language: fr\\n"\n'
        '"Language-Name: Francais\\n"\n\n'
        'msgid "Choose folder..."\n'
        'msgstr "Choisir un dossier..."\n',
        encoding="utf-8",
    )
    translation = Translation("fr", tmp_path)
    assert translation.display_name == "Francais"
    assert translation.gettext("Choose folder...") == "Choisir un dossier..."
    assert translation.gettext("Untranslated") == "Untranslated"