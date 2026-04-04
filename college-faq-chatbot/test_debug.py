import sys
sys.path.insert(0, "backend")
import modules.chatbot_core as core
import modules.context_manager as ctx

session = 'test12345'
mgr = ctx.get_context_manager()
mgr.update(session, intent='admissions', entities={}, response='hello', user_message='how to do admission?')
q = 'what is my college name/'
state = mgr.get(session)
is_short_followup = len(q.split()) <= 4
has_kw = q.lower().startswith(('and ', 'what about ', 'how about ', 'for '))
intent = core.predict_intent(q)

print(f'q len: {len(q.split())}')
print(f'is_short: {is_short_followup}')
print(f'has_kw: {has_kw}')
print(f'intent: {intent}')
print(f'state.last_intent: {state.last_intent}')
print(f'condition met? {(is_short_followup or has_kw) and intent=="general"}')
print()
print("OUTPUT:")
print(core.get_response(q, session))
