content = open('hf_space/app.py', encoding='utf-8').read()
# Move css to launch() for Gradio 6 compatibility
old = '''with gr.Blocks(
    title="SupportPulse Intelligence Platform",
    css="""
    body { background: #020617 !important; }
    .gradio-container { max-width: 1100px !important; }
    .gr-button-primary { background: #3b82f6 !important; border: none !important; }
    """
) as demo:'''
new = '''CUSTOM_CSS = """
    body { background: #020617 !important; }
    .gradio-container { max-width: 1100px !important; }
    .gr-button-primary { background: #3b82f6 !important; border: none !important; }
"""
with gr.Blocks(title="SupportPulse Intelligence Platform") as demo:'''
if old in content:
    content = content.replace(old, new)
    content = content.replace('demo.launch()', 'demo.launch(css=CUSTOM_CSS)')
    open('hf_space/app.py', 'w', encoding='utf-8').write(content)
    print('Fixed Gradio 6 css parameter')
else:
    print('Pattern not found - checking content...')
    idx = content.find('gr.Blocks')
    print(repr(content[idx:idx+200]))
