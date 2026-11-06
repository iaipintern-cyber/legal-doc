import sys
sys.path.insert(0, r'C:\Users\Idex\Documents\legal final\legal\legal\backend')
from services.military_law_service import select_rules, search_relevant_military_laws, get_all_military_laws, MILITARY_LAW_CATALOG, MILITARY_LAW_KNOWLEDGE_BASE

print('Catalog loaded:', len(MILITARY_LAW_CATALOG), 'rules')
print('Knowledge base:', len(MILITARY_LAW_KNOWLEDGE_BASE), 'rules (fallback)')

# test select_rules
results = select_rules('intoxication', max_results=5)
print('\nselect_rules("intoxication"):')
for r in results:
    print(f'  - {r["rule_or_section"]}')

# test with topic
results2 = select_rules('bonafide duty', topic='bonafide duty', max_results=3)
print('\nselect_rules("bonafide duty", topic="bonafide duty"):')
for r in results2:
    print(f'  - {r["rule_or_section"]}')

# test search_relevant_military_laws
results3 = search_relevant_military_laws('character reputation', max_results=4)
print('\nsearch_relevant_military_laws("character reputation"):')
for r in results3:
    print(f'  - {r["rule_or_section"]}')

# test get_all_military_laws
all_laws = get_all_military_laws()
print(f'\nget_all_military_laws: {len(all_laws)} rules (catalog)')

# test old-style still works
old = search_relevant_military_laws('intoxication', max_results=3)
print('\nOld-style search:')
for r in old:
    print(f'  - {r["rule_or_section"]}')