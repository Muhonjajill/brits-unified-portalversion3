# core/utilss/escalation_constants.py

ESCALATION_TIME_LIMITS = {
    'low': 8,      
    'medium': 2,
    'high': 1,
    'critical': 0.5,
}

ESCALATION_FLOW = {
    'Tier 1': 'Tier 2',
    'Tier 2': 'Tier 3',
    'Tier 3': 'Tier 4',
    'Tier 4': None,
}
