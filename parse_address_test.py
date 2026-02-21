import re

def parse_single_line_address(address_str: str) -> dict:
    if not address_str:
        return {}
        
    result = {}
    address_str = address_str.strip()
    
    # Common AU states
    states_re = r'\b(VIC|NSW|QLD|ACT|TAS|WA|SA|NT|VICTORIA|NEW SOUTH WALES|QUEENSLAND|TASMANIA|WESTERN AUSTRALIA|SOUTH AUSTRALIA|NORTHERN TERRITORY)\b'
    
    state_map = {
        'VICTORIA': 'VIC',
        'NEW SOUTH WALES': 'NSW',
        'QUEENSLAND': 'QLD',
        'TASMANIA': 'TAS',
        'WESTERN AUSTRALIA': 'WA',
        'SOUTH AUSTRALIA': 'SA',
        'NORTHERN TERRITORY': 'NT'
    }
    
    # 1. Street, Suburb State Postcode matches
    match = re.search(r'^(.*?)[\s,]+([A-Za-z\s]+?)[\s,]+' + states_re + r'[\s,]*(\d{4})\s*$', address_str, re.IGNORECASE)
    if match:
        street = match.group(1).strip().rstrip(',')
        city = match.group(2).strip().rstrip(',')
        state = match.group(3).upper()
        if state in state_map: state = state_map[state]
        postcode = match.group(4).strip()
        
        result['street'] = street
        result['city'] = city
        result['state'] = state
        result['postal_code'] = postcode
        result['country'] = 'AU'
        return result
        
    # 2. Street, State Postcode (no suburb)
    match_no_suburb = re.search(r'^(.*?)[\s,]+' + states_re + r'[\s,]*(\d{4})\s*$', address_str, re.IGNORECASE)
    if match_no_suburb:
        result['street'] = match_no_suburb.group(1).strip().rstrip(',')
        state = match_no_suburb.group(2).upper()
        if state in state_map: state = state_map[state]
        result['state'] = state
        result['postal_code'] = match_no_suburb.group(3).strip()
        result['country'] = 'AU'
        return result

    # 3. Street Suburb Postcode (no state)
    match_no_state = re.search(r'^(.*?)[\s,]+([A-Za-z\s]+?)[\s,]+(\d{4})\s*$', address_str, re.IGNORECASE)
    if match_no_state:
        result['street'] = match_no_state.group(1).strip().rstrip(',')
        result['city'] = match_no_state.group(2).strip().rstrip(',')
        result['postal_code'] = match_no_state.group(3).strip()
        return result
        
    return result

test_cases = [
    "123 Fake Street, Melbourne VIC 3000",
    "Unit 4/12 Test Rd Sydney NSW 2000",
    "45 Random Ave, Brisbane, Queensland, 4000",
    "99 Nowhere Lane Perth 6000",
    "100 Just Street, 3000"
]

for t in test_cases:
    print(f"'{t}' -> {parse_single_line_address(t)}")
