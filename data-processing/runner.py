from entities.abbreviations.expander import AbbreviationExpander

a = AbbreviationExpander()
print(*list(a.parse("", "Natural Langauge Processing (NLP) is a sub-field of artificial intelligence (AI).")), sep = '\n')
