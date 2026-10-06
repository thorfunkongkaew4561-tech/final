"""รัน Notebook ข้อ 2 ทั้ง EDA เตรียมข้อมูล ฝึกและประเมินตามลำดับ.

ใช้เฉพาะ Notebook ของโปรเจกต์นี้ เหมาะสำหรับตรวจ Run All จาก command line.
"""
import argparse
import base64
import contextlib
import io
import json
import os
from pathlib import Path

os.environ.setdefault('MPLBACKEND', 'Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / 'notebooks' / '02_market_occupancy_eda.ipynb'


def main():
    parser = argparse.ArgumentParser(description='รันและบันทึก outputs ของ Notebook ในโปรเจกต์')
    parser.add_argument('--notebook', default=str(NOTEBOOK), help='path ของ Notebook ที่ต้องการรัน')
    notebook_path = Path(parser.parse_args().notebook)
    if not notebook_path.is_absolute():
        notebook_path = ROOT / notebook_path
    notebook_path = notebook_path.resolve()
    if not notebook_path.is_relative_to(ROOT) or notebook_path.suffix != '.ipynb':
        raise ValueError('เลือกไฟล์ .ipynb ภายในโปรเจกต์เท่านั้น')
    notebook = json.loads(notebook_path.read_text(encoding='utf-8'))
    namespace = {'__name__': '__main__'}
    execution_count = 0
    os.chdir(ROOT)
    for cell in notebook['cells']:
        if cell['cell_type'] != 'code':
            continue
        execution_count += 1
        cell['execution_count'] = execution_count
        cell['outputs'] = []
        stdout = io.StringIO()

        def flush_stdout():
            output = stdout.getvalue()
            if output:
                cell['outputs'].append({'output_type': 'stream', 'name': 'stdout', 'text': output.splitlines(True)})
                stdout.seek(0)
                stdout.truncate(0)

        def capture_display(*objects):
            flush_stdout()
            for obj in objects:
                mime = {'text/plain': repr(obj)}
                if hasattr(obj, '_repr_markdown_'):
                    mime['text/markdown'] = obj._repr_markdown_()
                elif hasattr(obj, '_repr_html_'):
                    html = obj._repr_html_()
                    if html:
                        mime['text/html'] = html
                cell['outputs'].append({'output_type': 'display_data', 'data': mime, 'metadata': {}})

        def capture_figures(*args, **kwargs):
            flush_stdout()
            for number in plt.get_fignums():
                fig = plt.figure(number)
                buffer = io.BytesIO()
                fig.savefig(buffer, format='png', dpi=110, bbox_inches='tight')
                cell['outputs'].append({
                    'output_type': 'display_data',
                    'data': {'image/png': base64.b64encode(buffer.getvalue()).decode('ascii'), 'text/plain': 'EDA figure'},
                    'metadata': {},
                })
                plt.close(fig)

        plt.show = capture_figures
        # import cell ใช้ display ของ IPython ตั้งแต่ cell ถัดไปจึงแทนที่เพื่อเก็บผล
        if execution_count > 1:
            namespace['display'] = capture_display
        with contextlib.redirect_stdout(stdout):
            exec(compile(''.join(cell['source']), f'{notebook_path.name}:cell-{execution_count}', 'exec'), namespace)
        flush_stdout()
        print(f'Executed code cell {execution_count}')

    notebook_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'Saved executed notebook: {notebook_path}')


if __name__ == '__main__':
    main()
