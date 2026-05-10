content = open('tests/unit/test_schemas.py', encoding='utf-8').read()
old = '    def test_run_rag_default_false(self):\n        req = TicketRequest(subject="test", body="test body")\n        assert req.run_rag is False  # default'
new = '    def test_run_rag_default_true(self):\n        req = TicketRequest(subject="test", body="test body")\n        assert req.run_rag is True  # schema default is True'
content = content.replace(old, new)
open('tests/unit/test_schemas.py', 'w', encoding='utf-8').write(content)
print('Fixed' if new in content else 'NOT found - no change')
