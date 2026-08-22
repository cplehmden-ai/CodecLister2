# Eigene Sprachen

Eine Sprache wird als `translations/<code>.po` abgelegt, zum Beispiel
`translations/fr.po`. Die Datei verwendet das einfache gettext-PO-Format:

```po
msgid ""
msgstr ""
"Language: fr\n"
"Language-Name: Francais\n"

msgid "Choose folder..."
msgstr "Choisir un dossier..."
```

Nicht übersetzte Texte fallen automatisch auf Englisch zurück. Nach einem
Neustart erscheint die neue Sprache im Sprachmenü. `Language-Name` ist der im
Menü angezeigte Name.
