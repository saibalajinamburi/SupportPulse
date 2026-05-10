import json, urllib.request

url = 'https://api.github.com/repos/saibalajinamburi/SupportPulse/actions/runs/25634977238/jobs'
with urllib.request.urlopen(url) as r:
    data = json.loads(r.read())

for job in data['jobs']:
    print(f"JOB: {job['name']} => {job['conclusion']}")
    for step in job['steps']:
        icon = 'FAIL' if step['conclusion'] == 'failure' else 'ok  '
        print(f"  [{icon}] {step['name']}")
