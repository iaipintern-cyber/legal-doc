from backend.services.military_law_service import select_rules, search_relevant_military_laws, get_all_military_laws, MILITARY_LAW_CATALOG, MILITARY_LAW_KNOWLEDGE_BASE

# Test 1: Catalog loaded
print(f'Catalog rules: {len(MILITARY_LAW_CATALOG)}')
print(f'Knowledge base rules: {len(MILITARY_LAW_KNOWLEDGE_BASE)}')

# Test 2: select_rules with 'intoxication'
results = select_rules('intoxication', max_results=5)
print(f'\nselect_rules("intoxication"):')
for r in results:
    print(f'  - {r["rule_or_section"]}: {r["title"][:40]}...')

# Test 3: select_rules with topic 'bonafide duty'
results2 = select_rules('bonafide duty', topic='bonafide duty', max_results=3)
print(f'\nselect_rules("bonafide duty", topic="bonafide duty"):')
for r in results2:
    print(f'  - {r["rule_or_section"]}: {r["title"][:50]}...')

# Test 4: select_rules with rule_numbers
results3 = select_rules('intoxication', rule_numbers=['180', '48'], max_results=5)
print(f'\nselect_rules with rule_numbers=["180","48"]:')
for r in results3:
    print(f'  - {r["rule_or_section"]}')

# Test 5: search_relevant_military_laws (public API)
results4 = search_relevant_military_laws('character reputation', max_results=4)
print(f'\nsearch_relevant_military_laws("character reputation"):')
for r in results4:
    print(f'  - {r["rule_or_section"]}')

# Test 5: get_all_military_laws
all_laws = get_all_military_laws()
print(f'\nget_all_military_laws: {len(all_laws)} rules')

# Test 6: Backward compat - old function still works
old_results = search_relevant_military_laws('intoxication', max_results=3)
print(f'\nOld-style search_relevant_military_laws("intoxication"):')
for r in old_results:
    print(f'  - {r["rule_or_section"]}')