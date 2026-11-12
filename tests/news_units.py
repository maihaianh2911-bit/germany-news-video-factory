#!/usr/bin/env python3
"""Unit checks of the German text helpers (no network, no Whisper): the voice check's word comparison (numbers
written out on both sides) and the whole-word readings sent to the voice. Run from the repo root:
python3 tests/news_units.py   (needs num2words)"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'news'))
from voice_check import compare
from tts_lines import spoken

flagged = lambda sent, heard: compare(sent, heard)[1]

# a wrong number is a misreading; the same number written in digits or in words is not
assert flagged('Die Inflation liegt bei 3,5 Prozent.', 'Die Inflation liegt bei drei fünf Prozent.'), 'wrong decimal not flagged'
assert not flagged('Die Inflation liegt bei 3,5 Prozent.', 'Die Inflation liegt bei drei Komma fünf Prozent.')
assert not flagged('Die Inflation liegt bei 3,5 %.', 'Die Inflation liegt bei 3,5 Prozent.')
assert flagged('Der Mindestlohn steigt auf 14 Euro.', 'Der Mindestlohn steigt auf vier Euro.')
assert not flagged('Am 12. November kamen 1.000 Menschen.', 'Am zwölften November kamen tausend Menschen.')
assert not flagged('Am 1. Januar stieg er um 1 Prozent.', 'Am ersten Januar stieg er um ein Prozent.')
assert not flagged('Seit 1990 gilt § 5.', 'Seit neunzehnhundertneunzig gilt Paragraf fünf.')
assert not flagged('Er kam 2019. Dann ging er.', 'Er kam zweitausendneunzehn. Dann ging er.')
# short words must match exactly, long ones may differ only by spelling
assert flagged('Das ist ein Problem.', 'Das ist kein Problem.')
assert flagged('Das Bundesverfassungsgericht urteilt.', 'Das Bundesverwaltungsgericht urteilt.')
assert not flagged('Der Fluss ist breit.', 'Der Fluß ist breit.')

# readings replace whole words only, longest first, each once
rd = {'US': 'U S', 'EZB': 'E Z B', 'E': 'Eh'}
assert spoken({'lines': ['Die USA und die US-Regierung, die EZB.']}, rd) == ['Die USA und die U S-Regierung, die E Z B.']
assert spoken({'lines': ['US', 'x'], 'tts': {'2': 'eigener Text'}}, rd) == ['U S', 'eigener Text']
print('news unit checks OK')
